import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.utils import timezone

from external_sync.models import SyncBinding, SyncJob
from members.models import Group, Member, Parent

logger = logging.getLogger(__name__)


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
    SPOND_BIRTHDAY_FALLBACK_NOTE = (
        "Genauer Geburtstag wurde von Spond nicht übergeben. es wurde der 01. als Tag gesetzt."
    )

    def __init__(self):
        super().__init__(key="spond")

    def _credentials(self, job: SyncJob):
        creds = job.credentials or {}
        return self._credentials_from_dict(creds)

    def _credentials_from_dict(self, creds: dict):
        username = creds.get("username")
        password = creds.get("password")
        if not username or not password:
            raise ProviderNotImplementedError("Spond benötigt credentials.username und credentials.password.")
        return username, password

    def _extract_parent_group_id(self, group_payload: dict):
        parent_candidate = (
            group_payload.get("parentGroupId")
            or group_payload.get("parent_group_id")
            or group_payload.get("parentId")
            or group_payload.get("parent_id")
        )
        if parent_candidate:
            return str(parent_candidate)

        parent_obj = group_payload.get("parent")
        if isinstance(parent_obj, dict):
            parent_id = parent_obj.get("id")
            if parent_id:
                return str(parent_id)

        return ""

    def _is_top_level_group(self, group_payload: dict):
        is_subgroup = group_payload.get("isSubGroup")
        if is_subgroup is True:
            return False
        return not self._extract_parent_group_id(group_payload)

    def _filter_groups_by_top_level(self, groups_payload: list[dict], top_level_group_id: str):
        selected = []
        for group in groups_payload:
            group_id = str(group.get("id", ""))
            parent_group_id = self._extract_parent_group_id(group)
            if group_id == top_level_group_id or parent_group_id == top_level_group_id:
                selected.append(group)
        return selected

    def _extract_subgroups(self, group_payload: dict):
        for key in ("subGroups", "subgroups", "children"):
            candidate = group_payload.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
        return []

    def _extract_member_group_ids(self, member_data: dict):
        """Extract potential group IDs from member payload in deterministic order."""
        collected = []

        for key in ("subGroups", "subgroups", "subgroupIds", "subGroupIds", "groupIds", "group_ids"):
            value = member_data.get(key)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        item_id = str(item.get("id", "")).strip()
                    else:
                        item_id = str(item).strip()
                    if item_id:
                        collected.append(item_id)

        groups_value = member_data.get("groups")
        if isinstance(groups_value, list):
            for item in groups_value:
                if isinstance(item, dict):
                    item_id = str(item.get("id", "")).strip()
                else:
                    item_id = str(item).strip()
                if item_id:
                    collected.append(item_id)

        singular_group_id = str(
            self._pick(member_data, "subgroupId", "subGroupId", "groupId", "group_id") or ""
        ).strip()
        if singular_group_id:
            collected.append(singular_group_id)

        ordered_unique = []
        seen = set()
        for group_id in collected:
            if group_id in seen:
                continue
            seen.add(group_id)
            ordered_unique.append(group_id)
        return ordered_unique

    def _resolve_member_group_object(
        self,
        *,
        member_data: dict,
        context_group_external_id: str,
        context_group_obj: Group | None,
        group_map_by_external_id: dict,
        subgroup_external_ids: set,
    ):
        member_group_ids = self._extract_member_group_ids(member_data)
        if not member_group_ids and context_group_obj is not None:
            return context_group_obj

        # Prefer the first subgroup in payload order.
        for group_id in member_group_ids:
            if group_id in subgroup_external_ids and group_id in group_map_by_external_id:
                return group_map_by_external_id[group_id]

        # Then fallback to first known group in payload order.
        for group_id in member_group_ids:
            if group_id in group_map_by_external_id:
                return group_map_by_external_id[group_id]

        # Keep deterministic fallback to current context group.
        if context_group_external_id and context_group_external_id in group_map_by_external_id:
            return group_map_by_external_id[context_group_external_id]
        return context_group_obj

    def _groups_for_member_sync(self, groups_payload: list[dict]):
        """
        Normalize Spond groups for sync.

        If a top-level group contains one-level subgroups, we sync subgroups as local
        groups and assign members to those subgroup groups.
        """
        sync_groups = []
        seen_group_ids = set()

        for group in groups_payload:
            group_id = str(group.get("id", "")).strip()
            subgroups = self._extract_subgroups(group)

            if subgroups:
                for subgroup in subgroups:
                    subgroup_id = str(subgroup.get("id", "")).strip()
                    if not subgroup_id or subgroup_id in seen_group_ids:
                        continue

                    subgroup_payload = dict(subgroup)
                    if not self._extract_parent_group_id(subgroup_payload) and group_id:
                        subgroup_payload["parentGroupId"] = group_id

                    sync_groups.append(subgroup_payload)
                    seen_group_ids.add(subgroup_id)
                continue

            if not group_id or group_id in seen_group_ids:
                continue

            sync_groups.append(group)
            seen_group_ids.add(group_id)

        return sync_groups

    def _iter_member_sources(self, groups_payload: list[dict]):
        """Yield group contexts that can contain members, including one-level nested subgroups."""
        for group in groups_payload:
            if not isinstance(group, dict):
                continue

            group_id = str(group.get("id", "")).strip()
            yield group_id, group

            for subgroup in self._extract_subgroups(group):
                subgroup_id = str(subgroup.get("id", "")).strip()
                if not subgroup_id:
                    continue
                yield subgroup_id, subgroup

    def _is_group_sync_enabled(self, job: SyncJob):
        config = job.config or {}
        return bool(config.get("sync_groups", True))

    async def _fetch_all_groups(self, username: str, password: str):
        try:
            from spond import spond as spond_module
        except ImportError as exc:
            raise ProviderNotImplementedError("Python-Paket 'spond' ist nicht installiert.") from exc

        client = spond_module.Spond(username=username, password=password)
        try:
            groups = await client.get_groups()
            return groups or []
        finally:
            await client.clientsession.close()

    async def _fetch_groups(self, job: SyncJob):
        username, password = self._credentials(job)
        groups = await self._fetch_all_groups(username=username, password=password)

        # Optional: allow restricting to one selected top-level spond group
        # config: { "group_id": "..." }
        group_id = str((job.config or {}).get("group_id") or "").strip()
        if not group_id:
            return groups

        filtered_groups = self._filter_groups_by_top_level(groups, top_level_group_id=group_id)
        if filtered_groups:
            return filtered_groups
        return groups

    async def _list_top_level_groups_async(self, credentials: dict):
        username, password = self._credentials_from_dict(credentials or {})
        groups = await self._fetch_all_groups(username=username, password=password)
        top_level_groups = [group for group in groups if self._is_top_level_group(group)]
        top_level_groups.sort(key=lambda item: str(item.get("name") or ""))
        return [
            {
                "id": str(group.get("id")),
                "name": group.get("name") or f"Spond-{group.get('id')}",
            }
            for group in top_level_groups
            if group.get("id") is not None
        ]

    def list_top_level_groups(self, credentials: dict):
        return asyncio.run(self._list_top_level_groups_async(credentials=credentials))

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

    def _pick(self, data, *keys):
        for key in keys:
            value = data.get(key)
            if value is None:
                continue
            if isinstance(value, str):
                value = value.strip()
            if value in ("", [], {}):
                continue
            return value
        return ""

    def _parse_birthday(self, raw_value):
        try:
            if not raw_value:
                return None, False

            if isinstance(raw_value, datetime):
                return raw_value.date(), False
            if isinstance(raw_value, date):
                return raw_value, False

            if not isinstance(raw_value, str):
                return None, False

            value = raw_value.strip()
            if not value:
                return None, False

            # Normalize common delimiters and cut off time suffix if present.
            normalized = value.replace("/", "-").replace(".", "-")
            if "T" in normalized:
                normalized = normalized.split("T", 1)[0]
            elif " " in normalized:
                normalized = normalized.split(" ", 1)[0]

            # Spond uses day=99 when exact birthday day is unknown/unavailable.
            # We map this to day=01 and document the fallback in member notes.
            if re.fullmatch(r"\d{4}-\d{2}-99", normalized):
                normalized = f"{normalized[:8]}01"
                try:
                    return date.fromisoformat(normalized), True
                except ValueError:
                    return None, False

            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
                try:
                    return date.fromisoformat(normalized), False
                except ValueError:
                    return None, False

            for fmt in ("%d-%m-%Y", "%d-%m-%y"):
                try:
                    return datetime.strptime(normalized, fmt).date(), False
                except ValueError:
                    continue

            return None, False
        except Exception:
            return None, False

    def _extract_address(self, payload):
        address_payload = payload.get("address") if isinstance(payload.get("address"), dict) else {}

        street = self._pick(payload, "street", "addressLine1", "address_line1") or self._pick(
            address_payload, "street", "addressLine1", "address_line1"
        )
        zip_code = self._pick(payload, "zipCode", "zip_code", "postalCode", "postal_code") or self._pick(
            address_payload, "zipCode", "zip_code", "postalCode", "postal_code"
        )
        city = self._pick(payload, "city", "town") or self._pick(address_payload, "city", "town")

        return {
            "street": street,
            "zip_code": str(zip_code).strip() if zip_code else "",
            "city": city,
        }

    def _upsert_binding(self, *, job, object_type, external_id, content_type, object_id, defaults):
        """Synchronize bindings while respecting both unique constraints."""
        now = timezone.now()
        payload = {
            "external_name": defaults.get("external_name", ""),
            "is_deleted_in_source": defaults.get("is_deleted_in_source", False),
            "pending_garbage_collection": defaults.get("pending_garbage_collection", False),
            "last_seen_at": defaults.get("last_seen_at") or now,
            "managed_fields": defaults.get("managed_fields", []),
            "content_type": content_type,
            "object_id": object_id,
            "object_type": object_type,
            "external_id": external_id,
        }

        # Prefer existing external-id mapping. If absent, remap existing object mapping.
        binding = SyncBinding.objects.filter(
            job=job,
            object_type=object_type,
            external_id=external_id,
        ).first()
        if not binding:
            binding = SyncBinding.objects.filter(
                job=job,
                content_type=content_type,
                object_id=object_id,
            ).first()

        if binding:
            for field, value in payload.items():
                setattr(binding, field, value)
            try:
                binding.save(
                    update_fields=[
                        "external_name",
                        "is_deleted_in_source",
                        "pending_garbage_collection",
                        "last_seen_at",
                        "managed_fields",
                        "content_type",
                        "object_id",
                        "object_type",
                        "external_id",
                        "updated_at",
                    ]
                )
            except IntegrityError:
                # Concurrent insert/update: force a deterministic final state.
                SyncBinding.objects.filter(
                    job=job,
                    object_type=object_type,
                    external_id=external_id,
                ).update(**payload)
            return

        try:
            SyncBinding.objects.create(job=job, **payload)
        except IntegrityError:
            # Row appeared between read and create. Update by the strongest key first.
            updated = SyncBinding.objects.filter(
                job=job,
                content_type=content_type,
                object_id=object_id,
            ).update(**payload)
            if not updated:
                SyncBinding.objects.filter(
                    job=job,
                    object_type=object_type,
                    external_id=external_id,
                ).update(**payload)

    @transaction.atomic
    def run(self, job: SyncJob, triggered_by):
        started_at = timezone.now()
        fetched_groups_payload = asyncio.run(self._fetch_groups(job))
        sync_groups = self._is_group_sync_enabled(job)
        groups_payload = self._groups_for_member_sync(fetched_groups_payload) if sync_groups else []

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
        processed_member_external_ids = set()
        group_map_by_external_id = {}
        subgroup_external_ids = {
            str(group.get("id", "")).strip() for group in groups_payload if self._extract_parent_group_id(group)
        }

        if sync_groups:
            # Phase 1: ensure all groups exist and are mapped before assigning members.
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

                group_map_by_external_id[group_external_id] = group_obj

                self._upsert_binding(
                    job=job,
                    object_type=SyncBinding.ObjectType.GROUP,
                    external_id=group_external_id,
                    content_type=group_ct,
                    object_id=group_obj.id,
                    defaults={
                        "external_name": group_name,
                        "is_deleted_in_source": False,
                        "pending_garbage_collection": False,
                        "last_seen_at": timezone.now(),
                        "managed_fields": ["name", "department"],
                    },
                )

        # Phase 2: process members using resolved target groups.
        for context_group_external_id, group_data in self._iter_member_sources(fetched_groups_payload):
            context_group_obj = group_map_by_external_id.get(context_group_external_id)

            # Spond structure: group["members"] with optional member["guardians"]
            for member_data in group_data.get("members", []):
                member_external_id = str(member_data["id"])
                seen_member_external_ids.add(member_external_id)

                if member_external_id in processed_member_external_ids:
                    continue
                processed_member_external_ids.add(member_external_id)

                first_name = (self._pick(member_data, "firstName", "first_name", "name") or "").strip()
                last_name = (self._pick(member_data, "lastName", "last_name", "surname") or "").strip()
                email = (self._pick(member_data, "email") or "").strip()

                member_mobile = self._pick(member_data, "mobilePhone", "mobile_phone", "phoneNumber")
                member_phone = self._pick(member_data, "phone", "homePhone", "home_phone")
                if not member_phone:
                    member_phone = self._pick(member_data, "phoneNumber")

                member_address = self._extract_address(member_data)
                try:
                    member_birthday, birthday_day_fallback_used = self._parse_birthday(
                        self._pick(member_data, "birthday", "birthDate", "birthdate", "dateOfBirth", "dob")
                    )
                except Exception:
                    member_birthday = None
                    birthday_day_fallback_used = False

                member_obj, member_created = Member.objects.update_or_create(
                    name=first_name,
                    lastname=last_name,
                    defaults={
                        "email": email,
                        "mobile": member_mobile,
                        "phone": member_phone,
                        "birthday": member_birthday,
                        "street": member_address["street"],
                        "zip_code": member_address["zip_code"],
                        "city": member_address["city"],
                    },
                )
                if member_created:
                    stats["imported_members"] += 1
                else:
                    stats["updated_members"] += 1

                if job.scope == SyncJob.Scope.DEPARTMENT and job.department_id:
                    member_obj.departments.add(job.department_id)

                # Keep group relation consistent for synced member
                if sync_groups:
                    target_group_obj = self._resolve_member_group_object(
                        member_data=member_data,
                        context_group_external_id=context_group_external_id,
                        context_group_obj=context_group_obj,
                        group_map_by_external_id=group_map_by_external_id,
                        subgroup_external_ids=subgroup_external_ids,
                    )
                    extracted_group_ids = self._extract_member_group_ids(member_data)
                    if target_group_obj is not None:
                        member_obj.group = target_group_obj
                        member_obj.save(update_fields=["group"])
                        logger.debug(
                            "Spond sync group assignment: member_external_id=%s member=%s %s context_group=%s resolved_group=%s extracted_group_ids=%s",
                            member_external_id,
                            first_name,
                            last_name,
                            context_group_external_id,
                            target_group_obj.name,
                            extracted_group_ids,
                        )
                    else:
                        logger.warning(
                            "Spond sync could not resolve group: member_external_id=%s member=%s %s context_group=%s extracted_group_ids=%s",
                            member_external_id,
                            first_name,
                            last_name,
                            context_group_external_id,
                            extracted_group_ids,
                        )

                if birthday_day_fallback_used and self.SPOND_BIRTHDAY_FALLBACK_NOTE not in member_obj.notes:
                    member_obj.notes = (
                        f"{member_obj.notes}\n{self.SPOND_BIRTHDAY_FALLBACK_NOTE}".strip()
                        if member_obj.notes
                        else self.SPOND_BIRTHDAY_FALLBACK_NOTE
                    )
                    member_obj.save(update_fields=["notes"])

                self._upsert_binding(
                    job=job,
                    object_type=SyncBinding.ObjectType.MEMBER,
                    external_id=member_external_id,
                    content_type=member_ct,
                    object_id=member_obj.id,
                    defaults={
                        "external_name": f"{first_name} {last_name}".strip(),
                        "is_deleted_in_source": False,
                        "pending_garbage_collection": False,
                        "last_seen_at": timezone.now(),
                        "managed_fields": [
                            "name",
                            "lastname",
                            "email",
                            "phone",
                            "mobile",
                            "birthday",
                            "street",
                            "zip_code",
                            "city",
                            "group",
                        ],
                    },
                )

                # Guardians in Spond -> Parents in JF-Manager
                for guardian in member_data.get("guardians", []):
                    g_first = (self._pick(guardian, "firstName", "first_name", "name") or "").strip()
                    g_last = (self._pick(guardian, "lastName", "last_name", "surname") or "").strip()
                    g_email = (self._pick(guardian, "email") or "").strip()
                    g_mobile = self._pick(guardian, "mobilePhone", "mobile_phone", "phoneNumber")
                    g_phone = self._pick(guardian, "phone", "homePhone", "home_phone")
                    if not g_phone:
                        g_phone = self._pick(guardian, "phoneNumber")
                    g_address = self._extract_address(guardian)

                    # No parent object_type in SyncBinding yet, so we resolve by email/name.
                    parent_defaults = {
                        "name": g_first,
                        "lastname": g_last,
                        "phone": g_phone,
                        "mobile": g_mobile,
                        "street": g_address["street"],
                        "zip_code": g_address["zip_code"],
                        "city": g_address["city"],
                    }
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
        flagged_groups = 0
        if sync_groups:
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
