"""Audit legacy group assignments and explicitly bind one group to a role template."""

import hashlib
import json

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from departments.models import RoleTemplate
from departments.role_catalog import ROLE_SPECS

ROLE_SPEC_BY_KEY = {spec.key: spec for spec in ROLE_SPECS}
ORGANIZATION_SCOPE = "departments.can_access_all_departments"


def _snapshot(group, template=None):
    permissions = sorted(
        (permission.pk, f"{permission.content_type.app_label}.{permission.codename}")
        for permission in group.permissions.select_related("content_type")
    )
    department_assignments = sorted(
        (role.pk, role.user_id, role.department_id) for role in group.department_assignments.all()
    )
    snapshot = {
        "group_id": group.pk,
        "group_name": group.name,
        "permissions": permissions,
        "global_user_ids": sorted(group.user_set.values_list("pk", flat=True)),
        "staff_user_ids": sorted(group.user_set.filter(is_staff=True).values_list("pk", flat=True)),
        "department_assignments": department_assignments,
        "ldap_mapping_ids": sorted(group.ldap_role_mappings.values_list("pk", flat=True)),
        "oidc_mapping_ids": sorted(group.oidc_group_mappings.values_list("pk", flat=True)),
        "bound_template_key": getattr(group.role_template, "key", None) if hasattr(group, "role_template") else None,
        "target_template_key": template.key if template else None,
        "target_group_id": template.group_id if template else None,
        "target_scope": template.scope if template else None,
    }
    if template and template.group_id and template.group_id != group.pk:
        snapshot["previous_group"] = _snapshot(template.group)
    return snapshot


def _fingerprint(snapshot, expected_permissions):
    payload = {"snapshot": snapshot, "expected_permissions": sorted(expected_permissions)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _assignment_lines(snapshot):
    return (
        f"globale Benutzer-IDs={snapshot['global_user_ids']}; "
        f"Staff-IDs={snapshot['staff_user_ids']}; "
        f"Abteilungszuordnungen (Rolle/Benutzer/Abteilung)={snapshot['department_assignments']}; "
        f"LDAP-Mapping-IDs={snapshot['ldap_mapping_ids']}; "
        f"OIDC-Mapping-IDs={snapshot['oidc_mapping_ids']}"
    )


class Command(BaseCommand):
    help = "Django-Gruppen und Zuweisungen prüfen; eine Altgruppe nur nach Fingerprint-Bestätigung zuordnen."

    def add_arguments(self, parser):
        parser.add_argument("--template-key", help="Stabiler Schlüssel der Standardvorlage für den Vergleich.")
        parser.add_argument("--group-id", type=int, help="Datenbank-ID der vorhandenen Gruppe für den Vergleich.")
        parser.add_argument(
            "--apply", action="store_true", help="Explizite Zuordnung nach vorherigem Vergleich ausführen."
        )
        parser.add_argument("--expected", help="Fingerprint aus dem unmittelbar zuvor geprüften Vergleich.")

    def handle(self, *args, **options):
        key = options["template_key"]
        group_id = options["group_id"]
        applying = options["apply"]
        expected = options["expected"]
        if (key is None) != (group_id is None):
            raise CommandError("Für einen Vergleich sind --template-key und --group-id gemeinsam erforderlich.")
        if applying and (key is None or expected is None):
            raise CommandError("--apply verlangt --template-key, --group-id und --expected.")
        if expected and not applying:
            raise CommandError("--expected ist nur zusammen mit --apply erlaubt.")
        if key is None:
            self._audit_groups()
            return
        if key not in ROLE_SPEC_BY_KEY:
            raise CommandError(f"Unbekannter Standard-Vorlagenschlüssel: {key}")
        if applying:
            with transaction.atomic():
                self._compare_and_bind(key, group_id, expected)
        else:
            self._compare_and_bind(key, group_id, None)

    def _audit_groups(self):
        for group in Group.objects.order_by("pk"):
            snapshot = _snapshot(group)
            self.stdout.write(
                f"Gruppe {group.pk} {group.name!r}; Vorlage={snapshot['bound_template_key'] or '—'}; "
                f"Permissions={[name for _, name in snapshot['permissions']]}; {_assignment_lines(snapshot)}"
            )

    def _compare_and_bind(self, key, group_id, expected):
        spec = ROLE_SPEC_BY_KEY[key]
        group_query = Group.objects.select_for_update() if expected else Group.objects
        template_query = RoleTemplate.objects.select_for_update() if expected else RoleTemplate.objects
        try:
            group = group_query.get(pk=group_id)
        except Group.DoesNotExist as exc:
            raise CommandError("Gruppe existiert nicht.") from exc
        template = template_query.filter(key=key).first()
        if expected and template and template.group_id and template.group_id != group.pk:
            Group.objects.select_for_update().get(pk=template.group_id)

        snapshot = _snapshot(group, template)
        snapshot["target_template_key"] = key
        snapshot["target_template_exists"] = template is not None
        snapshot["target_scope"] = template.scope if template else spec.scope
        actual = {name for _, name in snapshot["permissions"]}
        desired = set(spec.permissions)
        fingerprint = _fingerprint(snapshot, desired)
        self.stdout.write(
            f"Vergleich: Vorlage={key}, vorhanden={template is not None}, "
            f"Gruppe={group.pk} {group.name!r}, Bereich={snapshot['target_scope']}"
        )
        self.stdout.write(f"Fehlende Permissions: {', '.join(sorted(desired - actual)) or '—'}")
        self.stdout.write(f"Zusätzliche Permissions: {', '.join(sorted(actual - desired)) or '—'}")
        self.stdout.write(_assignment_lines(snapshot))
        if "previous_group" in snapshot:
            previous = snapshot["previous_group"]
            self.stdout.write(
                f"Bisherige Vorlagengruppe={previous['group_id']} {previous['group_name']!r}; "
                f"Permissions={[name for _, name in previous['permissions']]}; {_assignment_lines(previous)}"
            )
        self.stdout.write(f"Fingerprint: {fingerprint}")
        if expected is None:
            return
        if expected != fingerprint:
            raise CommandError("Zustand seit dem Vergleich geändert; Zuordnung abgebrochen.")
        if template and (template.scope != spec.scope or template.is_archived):
            raise CommandError("Vorlagenbereich weicht vom Standard ab oder Vorlage ist archiviert.")
        if snapshot["bound_template_key"] not in (None, key):
            raise CommandError("Die Gruppe gehört bereits zu einer anderen Vorlage.")
        if (ORGANIZATION_SCOPE in actual) != (snapshot["target_scope"] == RoleTemplate.Scope.ORGANIZATION):
            raise CommandError("Organisationsberechtigung passt nicht zum Vorlagenbereich.")
        if snapshot["target_scope"] == RoleTemplate.Scope.DEPARTMENT and snapshot["global_user_ids"]:
            raise CommandError("Abteilungsvorlage kann keine global zugewiesene Gruppe übernehmen.")
        if snapshot["target_scope"] == RoleTemplate.Scope.ORGANIZATION and (
            snapshot["department_assignments"] or snapshot["ldap_mapping_ids"] or snapshot["oidc_mapping_ids"]
        ):
            raise CommandError(
                "Organisationsvorlage kann keine Abteilungszuweisungen oder externen Abbildung übernehmen."
            )
        if template and template.group_id == group.pk:
            self.stdout.write("Bereits zugeordnet; keine Änderungen.")
            return
        if template and template.group_id:
            old_snapshot = snapshot["previous_group"]
            if (
                old_snapshot["global_user_ids"]
                or old_snapshot["department_assignments"]
                or old_snapshot["ldap_mapping_ids"]
                or old_snapshot["oidc_mapping_ids"]
            ):
                raise CommandError("Bisherige Vorlagengruppe hat Zuweisungen; Umhängen verweigert.")
        if template is None:
            RoleTemplate.objects.create(
                key=spec.key,
                group=group,
                name=spec.name,
                description=spec.description,
                template_version=spec.version,
                scope=spec.scope,
                is_delegable=spec.is_delegable,
            )
        else:
            template.group = group
            template.save(update_fields=["group", "updated_at"])
        self.stdout.write(
            self.style.SUCCESS(f"Vorlage {key} mit Gruppe {group.pk} verbunden; Rechte/Zuweisungen unverändert.")
        )
