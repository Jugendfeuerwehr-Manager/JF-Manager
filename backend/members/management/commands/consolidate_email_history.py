"""
One-time data fix for the "mass mail flooding" bug.

Before the 'multiple' recipient type existed, sending a mail to several
individually-selected members created one separate EmailMessage per member
(looped on the frontend), flooding the E-Mail-Verlauf with near-identical
rows that only differ by recipient. This command retroactively merges those
historical rows into a single grouped EmailMessage (recipient_type="multiple"),
mirroring what new sends now produce natively (see EmailComposeView.vue /
MemberEmailService). It is safe to re-run; already-merged data has nothing
left to merge.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from members.models import EmailAttachment, EmailMessage, EmailRecipient

# Consecutive individual sends from the same loop happen within milliseconds;
# a generous window still avoids merging unrelated same-subject mails sent later.
DEFAULT_WINDOW_SECONDS = 30


class Command(BaseCommand):
    help = (
        "Merges historical flooded 'individual' EmailMessage entries (created by the old "
        "per-member send loop) into a single grouped 'multiple' EmailMessage."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--window-seconds",
            type=int,
            default=DEFAULT_WINDOW_SECONDS,
            help="Max gap between consecutive sends to still be considered part of the same batch.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only report what would be merged, without changing the database.",
        )

    def handle(self, *args, **options):
        window = timedelta(seconds=options["window_seconds"])
        dry_run = options["dry_run"]

        candidates = EmailMessage.objects.filter(recipient_type="individual").order_by(
            "sender_id", "subject", "body_html", "department_id", "created_at"
        )

        clusters = self._build_clusters(candidates, window)
        merge_clusters = [c for c in clusters if len(c) > 1]

        if not merge_clusters:
            self.stdout.write(self.style.SUCCESS("No flooded email batches found. Nothing to do."))
            return

        total_merged = sum(len(c) for c in merge_clusters)
        self.stdout.write(f"Found {len(merge_clusters)} batches to merge ({total_merged} rows total).")

        if dry_run:
            for cluster in merge_clusters:
                subjects = cluster[0].subject
                self.stdout.write(f"  - '{subjects}' x{len(cluster)} (ids: {[m.id for m in cluster]})")
            self.stdout.write(self.style.WARNING("Dry run: no changes made."))
            return

        with transaction.atomic():
            for cluster in merge_clusters:
                self._merge_cluster(cluster)

        self.stdout.write(self.style.SUCCESS(f"Merged {len(merge_clusters)} batches ({total_merged} rows)."))

    def _build_clusters(self, candidates, window):
        """Group consecutive same (sender, subject, body, department) messages sent within `window`."""
        clusters: list[list[EmailMessage]] = []
        current: list[EmailMessage] = []

        def same_group(a: EmailMessage, b: EmailMessage) -> bool:
            return (
                a.sender_id == b.sender_id
                and a.subject == b.subject
                and a.body_html == b.body_html
                and a.department_id == b.department_id
            )

        for message in candidates:
            if current and same_group(current[-1], message) and message.created_at - current[-1].created_at <= window:
                current.append(message)
            else:
                if current:
                    clusters.append(current)
                current = [message]
        if current:
            clusters.append(current)

        return clusters

    def _merge_cluster(self, cluster: list[EmailMessage]):
        """Merge a cluster of individual EmailMessages into the first one, converted to 'multiple'."""
        primary, duplicates = cluster[0], cluster[1:]

        member_ids = {m.recipient_member_id for m in cluster if m.recipient_member_id}
        primary.recipient_type = "multiple"
        primary.recipient_member = None
        primary.total_recipients = sum(m.total_recipients for m in cluster)
        primary.successful_sends = sum(m.successful_sends for m in cluster)
        primary.failed_sends = sum(m.failed_sends for m in cluster)
        primary.status = self._combined_status(cluster)
        primary.sent_at = max((m.sent_at for m in cluster if m.sent_at), default=primary.sent_at)
        primary.save(
            update_fields=[
                "recipient_type",
                "recipient_member",
                "total_recipients",
                "successful_sends",
                "failed_sends",
                "status",
                "sent_at",
            ]
        )
        primary.recipient_members.set(member_ids)

        # Re-parent child recipients/attachments onto the primary message, then drop the duplicates.
        for duplicate in duplicates:
            EmailRecipient.objects.filter(email_message=duplicate).update(email_message=primary)
            EmailAttachment.objects.filter(email_message=duplicate).delete()
            duplicate.delete()

    @staticmethod
    def _combined_status(cluster: list[EmailMessage]) -> str:
        statuses = {m.status for m in cluster}
        if statuses == {"sent"}:
            return "sent"
        if statuses == {"failed"}:
            return "failed"
        if statuses == {"draft"}:
            return "draft"
        if statuses == {"sending"}:
            return "sending"
        return "partial"
