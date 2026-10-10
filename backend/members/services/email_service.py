"""
Email sending service for member communications.
Handles recipient collection, personalization, and SMTP delivery.
"""

import logging
from dataclasses import dataclass, field

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from django.utils.html import strip_tags

from jf_manager_backend.html_safety import escape_html_text, sanitize_rich_html
from members.models import EmailMessage, EmailRecipient, Group, Member, Parent

logger = logging.getLogger(__name__)


# Personalisation tokens understood by EmailTemplateRenderer.render_for_member.
PERSONALIZATION_KEYS = ("vorname", "nachname", "vollername")


def uses_personalization(*texts: str) -> bool:
    """True when any text contains a member variable, so each member needs its own message."""
    return any(f"{{{{{key}}}}}" in (text or "") for text in texts for key in PERSONALIZATION_KEYS)


def _valid_address(address: str) -> bool:
    try:
        validate_email(address)
    except DjangoValidationError:
        return False
    return True


@dataclass
class RecipientResolution:
    """Outcome of a recipient check (UX-07.1).

    ``recipients`` are the deliveries that will be created: one per address, or one per
    address *and* member when the message is personalised, so two different personalised
    messages are never merged only because they share an address. ``excluded`` lists
    members or addresses that receive nothing, each with a reason code and text.
    """

    recipients: list[dict] = field(default_factory=list)
    excluded: list[dict] = field(default_factory=list)
    merged_duplicates: int = 0
    member_count: int = 0
    personalized: bool = False

    def as_dict(self) -> dict:
        return {
            "count": len(self.recipients),
            "member_count": self.member_count,
            "personalized": self.personalized,
            "merged_duplicates": self.merged_duplicates,
            "recipients": self.recipients,
            "excluded": self.excluded,
        }


class EmailRecipientCollector:
    """
    Collects email addresses for members based on recipient type.
    Handles parent emails, invalid addresses and deduplication.
    """

    EXCLUSION_REASONS = {
        "no_address": "Keine E-Mail-Adresse bei Mitglied oder Eltern hinterlegt",
        "invalid_address": "E-Mail-Adresse ist ungültig",
    }

    @staticmethod
    def _candidate_addresses(member: Member) -> list[dict]:
        """Every non-empty address of a member and its parents, in delivery order."""
        candidates = []
        for parent in Parent.objects.filter(children=member).distinct().order_by("pk"):
            for address in (parent.email, parent.email2):
                if address and address.strip():
                    candidates.append({"email": address.strip(), "name": parent.get_full_name(), "relation": "parent"})
        if member.email and member.email.strip():
            candidates.append({"email": member.email.strip(), "name": member.get_full_name(), "relation": "member"})
        return candidates

    @classmethod
    def get_member_emails(cls, member: Member) -> list[dict[str, str]]:
        """Valid, distinct addresses of one member (parents first, then the member)."""
        emails = []
        seen: set[str] = set()
        for candidate in cls._candidate_addresses(member):
            key = candidate["email"].lower()
            if key in seen or not _valid_address(candidate["email"]):
                continue
            seen.add(key)
            emails.append(
                {
                    "email": candidate["email"],
                    "name": candidate["name"],
                    "relation": candidate["relation"],
                    "member_id": member.id,
                    "member_name": member.get_full_name(),
                }
            )
        return emails

    @classmethod
    def resolve(cls, members, *, personalized: bool = False) -> RecipientResolution:
        """Resolve deliveries and exclusions for the given members."""
        resolution = RecipientResolution(personalized=personalized)
        seen: set = set()
        for member in members:
            resolution.member_count += 1
            member_name = member.get_full_name()
            candidates = cls._candidate_addresses(member)
            valid = []
            for candidate in candidates:
                if _valid_address(candidate["email"]):
                    valid.append(candidate)
                else:
                    resolution.excluded.append(
                        {
                            "member_id": member.id,
                            "member_name": member_name,
                            "email": candidate["email"],
                            "relation": candidate["relation"],
                            "reason_code": "invalid_address",
                            "reason": cls.EXCLUSION_REASONS["invalid_address"],
                        }
                    )
            if not valid:
                if not candidates:
                    resolution.excluded.append(
                        {
                            "member_id": member.id,
                            "member_name": member_name,
                            "email": "",
                            "relation": "",
                            "reason_code": "no_address",
                            "reason": cls.EXCLUSION_REASONS["no_address"],
                        }
                    )
                continue
            for candidate in valid:
                address = candidate["email"].lower()
                key = (address, member.id) if personalized else address
                if key in seen:
                    resolution.merged_duplicates += 1
                    continue
                seen.add(key)
                resolution.recipients.append(
                    {
                        "email": candidate["email"],
                        "name": candidate["name"],
                        "relation": candidate["relation"],
                        "member_id": member.id,
                        "member_name": member_name,
                    }
                )
        return resolution

    @staticmethod
    def members_for(recipient_type, *, group=None, member=None, members=None, member_qs=None):
        """Members targeted by a selection, restricted to ``member_qs`` (department scope)."""
        base_qs = member_qs if member_qs is not None else Member.objects.all()
        if recipient_type == "all":
            selected = base_qs
        elif recipient_type == "group":
            selected = base_qs.filter(group=group) if group is not None else base_qs.none()
        elif recipient_type == "individual":
            selected = base_qs.filter(pk=member.pk) if member is not None else base_qs.none()
        elif recipient_type == "multiple":
            selected = base_qs.filter(id__in=[m.id if hasattr(m, "id") else m for m in (members or [])])
        else:
            raise ValueError(f"Invalid recipient type: {recipient_type}")
        return selected.order_by("lastname", "name", "pk").distinct()

    @classmethod
    def get_recipients_for_all_members(cls, member_qs=None) -> list[dict[str, str]]:
        """Get all recipients for all members in scope."""
        return cls.resolve(cls.members_for("all", member_qs=member_qs)).recipients

    @classmethod
    def get_recipients_for_group(cls, group: Group, member_qs=None) -> list[dict[str, str]]:
        """Get all recipients for members in a specific group."""
        return cls.resolve(cls.members_for("group", group=group, member_qs=member_qs)).recipients

    @classmethod
    def get_recipients_for_member(cls, member: Member) -> list[dict[str, str]]:
        """Get all recipients for a single member."""
        return cls.get_member_emails(member)

    @classmethod
    def get_recipients_for_members(cls, members, member_qs=None) -> list[dict[str, str]]:
        """Get all recipients for an explicit list/queryset of members (grouped 'multiple' send)."""
        return cls.resolve(cls.members_for("multiple", members=list(members), member_qs=member_qs)).recipients


class EmailTemplateRenderer:
    """
    Handles template variable rendering for personalized emails.
    Supports variables like {{vorname}}, {{nachname}}, etc.
    """

    @staticmethod
    def get_available_variables() -> list[dict[str, str]]:
        """
        Returns list of available template variables.
        Each dict contains 'variable' and 'description'.
        """
        return [
            {"variable": "{{vorname}}", "description": "Vorname des Mitglieds"},
            {"variable": "{{nachname}}", "description": "Nachname des Mitglieds"},
            {"variable": "{{vollername}}", "description": "Vollständiger Name des Mitglieds"},
        ]

    @staticmethod
    def render_for_member(
        template_html: str, template_text: str, member: Member, signature: str = "", layout: str = "none"
    ) -> tuple:
        """
        Render template with member-specific data.

        Args:
            template_html: HTML template string
            template_text: Plain text template string
            member: Member instance
            signature: User's email signature
            layout: Visual layout name (none / general / important / events)

        Returns:
            Tuple of (rendered_html, rendered_text)
        """
        context_data = {
            "vorname": member.name,
            "nachname": member.lastname,
            "vollername": member.get_full_name(),
        }

        # Simple string replacement for variables
        rendered_html = sanitize_rich_html(template_html)
        rendered_text = template_text

        for key, value in context_data.items():
            rendered_html = rendered_html.replace(f"{{{{{key}}}}}", escape_html_text(value))
            rendered_text = rendered_text.replace(f"{{{{{key}}}}}", value or "")

        # Add signature if provided
        if signature:
            rendered_html += f"<br><br>{sanitize_rich_html(signature)}"
            # Strip HTML from signature for text version
            text_signature = strip_tags(sanitize_rich_html(signature))
            rendered_text += f"\n\n{text_signature}"

        # Wrap in layout template if requested
        if layout and layout != "none":
            from django.template import Context, Template
            from django.template.loader import render_to_string
            from django.utils.safestring import mark_safe

            from orders.models import EmailLayoutTemplate

            layout_context = {
                "content": mark_safe(rendered_html),
                "site_name": "JF-Manager",
                "preview_text": "",
            }
            try:
                db_layout = EmailLayoutTemplate.objects.filter(layout_type=layout).first()
                if db_layout:
                    tpl = Template(db_layout.html_content)
                    rendered_html = tpl.render(Context(layout_context))
                else:
                    rendered_html = render_to_string(f"email_layouts/{layout}.html", layout_context)
            except Exception:
                logger.warning("Layout template '%s' not found; sending without layout.", layout)

        return sanitize_rich_html(rendered_html), rendered_text


class MemberEmailService:
    """
    Main service for sending emails to members and their parents.
    """

    @staticmethod
    @transaction.atomic
    def create_email_message(
        sender,
        subject: str,
        body_html: str,
        body_text: str,
        recipient_type: str,
        recipient_group: Group | None = None,
        recipient_member: Member | None = None,
        recipient_members: list[Member] | None = None,
    ) -> EmailMessage:
        """
        Create a new email message record.

        Args:
            sender: User sending the email
            subject: Email subject
            body_html: HTML body
            body_text: Plain text body
            recipient_type: 'all', 'group', 'individual', or 'multiple'
            recipient_group: Group instance if recipient_type is 'group'
            recipient_member: Member instance if recipient_type is 'individual'
            recipient_members: Member instances if recipient_type is 'multiple'

        Returns:
            EmailMessage instance
        """
        email_message = EmailMessage.objects.create(
            sender=sender,
            subject=subject,
            body_html=sanitize_rich_html(body_html),
            body_text=body_text or strip_tags(sanitize_rich_html(body_html)),
            recipient_type=recipient_type,
            recipient_group=recipient_group,
            recipient_member=recipient_member,
            status="draft",
        )

        if recipient_members:
            email_message.recipient_members.set(recipient_members)

        return email_message

    @staticmethod
    def resolve_recipients(email_message: EmailMessage, member_qs=None) -> RecipientResolution:
        """Recipient check for a stored message; same rules as the check before sending."""
        members = EmailRecipientCollector.members_for(
            email_message.recipient_type,
            group=email_message.recipient_group,
            member=email_message.recipient_member,
            members=list(email_message.recipient_members.all()),
            member_qs=member_qs,
        )
        return EmailRecipientCollector.resolve(
            members, personalized=uses_personalization(email_message.body_html, email_message.body_text)
        )

    @staticmethod
    @transaction.atomic
    def prepare_recipients(email_message: EmailMessage, member_qs=None) -> int:
        """
        Prepare recipient list for an email message.
        Creates EmailRecipient records for each recipient.

        Args:
            email_message: The EmailMessage to prepare recipients for
            member_qs: Optional queryset to restrict member scope (department filtering)

        Returns:
            Number of recipients prepared
        """
        resolution = MemberEmailService.resolve_recipients(email_message, member_qs=member_qs)
        members_by_id = {
            member.pk: member
            for member in Member.objects.filter(pk__in={item["member_id"] for item in resolution.recipients})
        }

        # Note: Signature is already included in body_html by the frontend
        for recipient_data in resolution.recipients:
            member = members_by_id.get(recipient_data["member_id"])

            # Personalize content for this member
            personalized_html, personalized_text = EmailTemplateRenderer.render_for_member(
                email_message.body_html,
                email_message.body_text,
                member,
                layout=getattr(email_message, "layout", "none") or "none",
            )

            EmailRecipient.objects.create(
                email_message=email_message,
                member=member,
                email_address=recipient_data["email"],
                recipient_name=recipient_data["name"],
                personalized_body_html=personalized_html,
                personalized_body_text=personalized_text,
                status="pending",
            )

        # Update email message with recipient count
        total_recipients = len(resolution.recipients)
        email_message.total_recipients = total_recipients
        email_message.save(update_fields=["total_recipients"])

        return total_recipients

    @staticmethod
    @transaction.atomic
    def send_email_message(email_message: EmailMessage) -> dict[str, int]:
        """
        Send an email message to all its recipients.

        Returns:
            Dict with 'successful' and 'failed' counts
        """
        email_message.status = "sending"
        email_message.save(update_fields=["status"])

        successful = 0
        failed = 0

        # Pre-load attachments
        attachments = list(email_message.attachments.all())

        pending_recipients = email_message.recipients.filter(status="pending")

        for recipient in pending_recipients:
            try:
                # Create email
                email = EmailMultiAlternatives(
                    subject=email_message.subject,
                    body=recipient.personalized_body_text,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[recipient.email_address],
                )

                # Attach HTML version
                email.attach_alternative(sanitize_rich_html(recipient.personalized_body_html), "text/html")

                # Attach files
                for attachment in attachments:
                    try:
                        attachment.file.seek(0)
                        email.attach(
                            attachment.original_filename,
                            attachment.file.read(),
                            attachment.content_type or "application/octet-stream",
                        )
                    except Exception as attach_err:
                        logger.warning(f"Could not attach file {attachment.original_filename}: {attach_err}")

                # Send
                email.send(fail_silently=False)

                # Mark as sent
                recipient.status = "sent"
                recipient.sent_at = timezone.now()
                recipient.save(update_fields=["status", "sent_at"])

                successful += 1

            except Exception as e:
                logger.error(f"Failed to send email to {recipient.email_address}: {e!s}")

                recipient.status = "failed"
                recipient.error_message = str(e)[:1000]  # Limit error message length
                recipient.save(update_fields=["status", "error_message"])

                failed += 1

        # Update email message status
        email_message.successful_sends = successful
        email_message.failed_sends = failed
        email_message.sent_at = timezone.now()

        if failed == 0:
            email_message.status = "sent"
        elif successful == 0:
            email_message.status = "failed"
            email_message.error_message = "Alle E-Mails konnten nicht zugestellt werden"
        else:
            email_message.status = "partial"
            email_message.error_message = f"{failed} von {successful + failed} E-Mails konnten nicht zugestellt werden"

        email_message.save()

        return {"successful": successful, "failed": failed}
