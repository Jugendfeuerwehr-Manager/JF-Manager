"""Create built-in role groups once and show drift without overwriting it."""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from departments.models import RoleTemplate
from departments.role_catalog import ROLE_SPECS


def _permission_map(required_names):
    result = {}
    for permission in Permission.objects.select_related("content_type"):
        name = f"{permission.content_type.app_label}.{permission.codename}"
        if name not in required_names:
            continue
        if name in result:
            raise CommandError(f"Mehrdeutige Django-Permission: {name}")
        result[name] = permission
    return result


def _actual_permissions(group):
    if group is None:
        return set()
    return {
        f"{permission.content_type.app_label}.{permission.codename}"
        for permission in group.permissions.select_related("content_type")
    }


def _differences(spec, template):
    if template.group_id is None:
        return ["keine Django-Gruppe gebunden"]
    differences = []
    for field, expected in (
        ("name", spec.name),
        ("description", spec.description),
        ("template_version", spec.version),
        ("scope", spec.scope),
        ("is_delegable", spec.is_delegable),
        ("is_archived", False),
    ):
        if getattr(template, field) != expected:
            differences.append(f"{field}: Ist={getattr(template, field)!r}, Soll={expected!r}")
    if template.group.name != spec.group_name:
        differences.append(f"group.name: Ist={template.group.name!r}, Soll={spec.group_name!r}")
    actual = _actual_permissions(template.group)
    desired = set(spec.permissions)
    if actual != desired:
        differences.append(f"Permissions fehlen: {', '.join(sorted(desired - actual)) or '—'}")
        differences.append(f"Permissions zusätzlich: {', '.join(sorted(actual - desired)) or '—'}")
    return differences


class Command(BaseCommand):
    help = "Standard-Rollenvorlagen einmalig anlegen und bestehende Gruppen nur vergleichen."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Nur Soll/Ist-Plan ausgeben, nichts anlegen.")

    @transaction.atomic
    def handle(self, *args, **options):
        keys = [spec.key for spec in ROLE_SPECS]
        names = [spec.group_name for spec in ROLE_SPECS]
        if len(set(keys)) != len(keys) or len(set(names)) != len(names):
            raise CommandError("Doppelte Schlüssel oder Gruppennamen im Rollenkatalog.")

        required_names = {name for spec in ROLE_SPECS for name in spec.permissions}
        permission_map = _permission_map(required_names)
        missing_permissions = sorted(required_names - permission_map.keys())
        if missing_permissions:
            raise CommandError(f"Fehlende Django-Permissions: {', '.join(missing_permissions)}")

        templates = {
            template.key: template for template in RoleTemplate.objects.select_related("group").filter(key__in=keys)
        }
        group_names = {group.name: group for group in Group.objects.filter(name__in=names)}
        collisions = []
        changes = []
        for spec in ROLE_SPECS:
            template = templates.get(spec.key)
            if template is None:
                if spec.group_name in group_names:
                    collisions.append(spec.key)
                else:
                    changes.append(spec)
                    self.stdout.write(f"NEU {spec.key}: {len(spec.permissions)} Permissions")
                continue
            differences = _differences(spec, template)
            if differences:
                self.stdout.write(f"ABWEICHUNG {spec.key}: {'; '.join(differences)}")
            else:
                self.stdout.write(f"UNVERÄNDERT {spec.key}")

        if collisions:
            raise CommandError(
                "Gruppenname bereits ohne Vorlagenbindung vorhanden; keine Namensübernahme: " + ", ".join(collisions)
            )
        if options["dry_run"]:
            self.stdout.write(f"Trockenlauf: {len(changes)} neue Vorlagen; keine Änderungen.")
            return

        for spec in changes:
            group = Group.objects.create(name=spec.group_name)
            group.permissions.set([permission_map[name] for name in spec.permissions])
            RoleTemplate.objects.create(
                key=spec.key,
                group=group,
                name=spec.name,
                description=spec.description,
                template_version=spec.version,
                scope=spec.scope,
                is_delegable=spec.is_delegable,
            )
        self.stdout.write(self.style.SUCCESS(f"{len(changes)} neue Vorlagen angelegt; bestehende unverändert."))
