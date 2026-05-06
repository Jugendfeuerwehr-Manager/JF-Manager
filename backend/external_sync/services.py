import asyncio
from dataclasses import dataclass

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from external_sync.models import SyncBinding, SyncJob
from members.models import Group, Member, Parent


class ProviderNotImplementedError(NotImplementedError):
    """Raised when a sync provider exists conceptually but is not implemented yet."""


@dataclass
class BaseExternalSyncProvider:
    key: str

    def test_connection(self, job):
        raise ProviderNotImplementedError(f"Der Provider '{self.key}' ist noch nicht implementiert.")

    def run(self, job, triggered_by):
        raise ProviderNotImplementedError(f"Der Provider '{self.key}' ist noch nicht implementiert.")


class SpondExternalSyncProvider(BaseExternalSyncProvider):
    def __init__(self):
        super().__init__(key="spond")

    def _credentials(self, job: SyncJob):
        creds = job.credentials or {}
        username = creds.get("username")
        password = creds.get("password")
        if not username or not password:
            raise ProviderNotImplementedError("Spond benötigt credentials.username und credentials.password.")
        return username, password

    async def _fetch_groups(self, job: SyncJob):
        try:
            from spond import spond as spond_module
        except ImportError as exc:
            raise ProviderNotImplementedError("Python-Paket 'spond' ist nicht installiert.") from exc

        username, password = self._credentials(job)
        client = spond_module.Spond(username=username, password=password)
        try:
            # Optional: allow restricting to one spond group in config
            # config: { "group_id": "..." }
            group_id = (job.config or {}).get("group_id")
            if group_id:
                group = await client.get_group(group_id)
                return [group]
            groups = await client.get_groups()
            return groups or []
        finally:
            await client.clientsession.close()

    async def _test_connection_async(self, job: SyncJob):
        try:
            from spond import spond as spond_module
        except ImportError as exc:
            raise ProviderNotImplementedError("Python-Paket 'spond' ist nicht installiert.") from exc

        username, password = self._credentials(job)
        client = spond_module.Spond(username=username, password=password)
        try:
            # Real API call from package; triggers auth and verifies account access.
            profile = await client.get_profile()
            return {
                "ok": True,
                "message": "Spond-Verbindung erfolgreich getestet.",
                "profile_id": profile.get("id"),
            }
        finally:
            await client.clientsession.close()

    def test_connection(self, job: SyncJob):
        return asyncio.run(self._test_connection_async(job))

    @transaction.atomic
    def run(self, job: SyncJob, triggered_by):
        started_at = timezone.now()
        groups_payload = asyncio.run(self._fetch_groups(job))

        stats = {
            "started_at": started_at,
            "finished_at": started_at,
            "imported_members": 0,
            "imported_groups": 0,
            "updated_members": 0,
            "updated_groups": 0,
            "flagged_for_review": 0,
            "deleted_objects": 0,
            "provider": "spond",
        }

        group_ct = ContentType.objects.get_for_model(Group)
        member_ct = ContentType.objects.get_for_model(Member)

        seen_group_external_ids = set()
        seen_member_external_ids = set()

        for group_data in groups_payload:
            group_external_id = str(group_data["id"])
            group_name = group_data.get("name") or f"Spond-{group_external_id}"
            seen_group_external_ids.add(group_external_id)

            group_defaults = {"name": group_name}
            if job.scope == SyncJob.Scope.DEPARTMENT and job.department_id:
                group_defaults["department_id"] = job.department_id

            group_obj, group_created = Group.objects.update_or_create(
                name=group_name,
                defaults=group_defaults,
            )
            if group_created:
                stats["imported_groups"] += 1
            else:
                stats["updated_groups"] += 1

            SyncBinding.objects.update_or_create(
                job=job,
                object_type=SyncBinding.ObjectType.GROUP,
                external_id=group_external_id,
                defaults={
                    "external_name": group_name,
                    "content_type": group_ct,
                    "object_id": group_obj.id,
                    "is_deleted_in_source": False,
                    "pending_garbage_collection": False,
                    "last_seen_at": timezone.now(),
                    "managed_fields": ["name", "department"],
                },
            )

            # Spond structure: group["members"] with optional member["guardians"]
            for member_data in group_data.get("members", []):
                member_external_id = str(member_data["id"])
                seen_member_external_ids.add(member_external_id)

                first_name = (member_data.get("firstName") or "").strip()
                last_name = (member_data.get("lastName") or "").strip()
                email = (member_data.get("email") or "").strip()

                member_obj, member_created = Member.objects.update_or_create(
                    name=first_name,
                    lastname=last_name,
                    defaults={
                        "email": email,
                        "mobile": (member_data.get("phoneNumber") or "").strip(),
                    },
                )
                if member_created:
                    stats["imported_members"] += 1
                else:
                    stats["updated_members"] += 1

                if job.scope == SyncJob.Scope.DEPARTMENT and job.department_id:
                    member_obj.departments.add(job.department_id)

                # Keep group relation consistent for synced member
                member_obj.group = group_obj
                member_obj.save(update_fields=["group"])

                SyncBinding.objects.update_or_create(
                    job=job,
                    object_type=SyncBinding.ObjectType.MEMBER,
                    external_id=member_external_id,
                    defaults={
                        "external_name": f"{first_name} {last_name}".strip(),
                        "content_type": member_ct,
                        "object_id": member_obj.id,
                        "is_deleted_in_source": False,
                        "pending_garbage_collection": False,
                        "last_seen_at": timezone.now(),
                        "managed_fields": ["name", "lastname", "email", "mobile", "group"],
                    },
                )

                # Guardians in Spond -> Parents in JF-Manager
                for guardian in member_data.get("guardians", []):
                    g_first = (guardian.get("firstName") or "").strip()
                    g_last = (guardian.get("lastName") or "").strip()
                    g_email = (guardian.get("email") or "").strip()

                    # No parent object_type in SyncBinding yet, so we resolve by email/name.
                    parent_defaults = {"name": g_first, "lastname": g_last}
                    if g_email:
                        parent_defaults["email"] = g_email

                    parent_obj, _ = Parent.objects.update_or_create(
                        email=g_email if g_email else "",
                        name=g_first,
                        lastname=g_last,
                        defaults=parent_defaults,
                    )
                    parent_obj.children.add(member_obj)

        # Flag missing groups/members for review.
        flagged_groups = (
            job.bindings.filter(object_type=SyncBinding.ObjectType.GROUP)
            .exclude(external_id__in=seen_group_external_ids)
            .update(
                is_deleted_in_source=True,
                pending_garbage_collection=True,
                last_seen_at=timezone.now(),
            )
        )
        flagged_members = (
            job.bindings.filter(object_type=SyncBinding.ObjectType.MEMBER)
            .exclude(external_id__in=seen_member_external_ids)
            .update(
                is_deleted_in_source=True,
                pending_garbage_collection=True,
                last_seen_at=timezone.now(),
            )
        )
        stats["flagged_for_review"] = flagged_groups + flagged_members
        stats["finished_at"] = timezone.now()
        return stats


PROVIDERS = {
    "spond": SpondExternalSyncProvider(),
    "hi_org": BaseExternalSyncProvider(key="hi_org"),
}


def get_provider(provider_key):
    try:
        return PROVIDERS[provider_key]
    except KeyError as exc:
        raise ProviderNotImplementedError(f"Unbekannter Provider '{provider_key}'.") from exc
