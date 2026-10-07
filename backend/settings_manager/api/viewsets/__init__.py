"""
ViewSets for Settings API
"""

from contextlib import suppress

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import transaction
from drf_spectacular.utils import extend_schema
from dynamic_preferences.registries import global_preferences_registry
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from settings_manager.models import LDAPConfig, OIDCConfig
from users.ldap_tls import apply_ldap_tls_options
from users.step_up import StepUpForWrites

from ..serializers import (
    AllSettingsSerializer,
    CategorySettingsUpdateSerializer,
    EmailSettingsSerializer,
    GeneralSettingsSerializer,
    LDAPConnectionTestSerializer,
    LDAPSettingsSerializer,
    MemberSettingsSerializer,
    OIDCDiscoveryResultSerializer,
    OIDCSettingsSerializer,
    OrderSettingsSerializer,
    ServiceSettingsSerializer,
    TrainingSettingsSerializer,
    UserPermissionsSerializer,
    VocabularySettingsSerializer,
)

# Import email template viewset
from .email_layout_template import EmailLayoutTemplateViewSet
from .email_template import EmailTemplateViewSet
from .ldap_mappings import LDAPDepartmentMappingViewSet
from .oidc_mappings import OIDCGroupMappingViewSet

__all__ = [
    "EmailLayoutTemplateViewSet",
    "EmailTemplateViewSet",
    "LDAPDepartmentMappingViewSet",
    "OIDCGroupMappingViewSet",
    "SettingsViewSet",
]


class SettingsViewSet(viewsets.ViewSet):
    """
    ViewSet for managing application settings

    Provides endpoints to:
    - List all settings (GET /settings/)
    - Get settings by category (GET /settings/general/, /settings/email/, etc.)
    - Update settings by category (PATCH /settings/general/, etc.)
    - Get user permissions (GET /settings/permissions/)
    """

    permission_classes = [IsAuthenticated]

    # Mapping of category to preference prefix
    CATEGORY_MAPPINGS = {
        "general": {"prefix": "general", "fields": ["title", "slug", "logo_url", "brand_color"]},
        "email": {
            "prefix": "email",
            "fields": [
                "email_host",
                "email_port",
                "email_use_tls",
                "email_use_ssl",
                "email_host_user",
                "email_host_password",
                "default_from_email",
            ],
        },
        "member": {"prefix": "members", "fields": ["alert_threshold", "alert_threshold_last_entries"]},
        "service": {"prefix": "service", "fields": ["service_start_time", "service_end_time"]},
        "order": {"prefix": "orders", "fields": ["equipment_manager_email"]},
        "ldap": {"prefix": "ldap", "fields": []},
        "oidc": {"prefix": "oidc", "fields": []},
        "security": {"prefix": "security", "fields": []},
        "push": {"prefix": "push", "fields": []},
        "training": {
            "prefix": "training",
            "fields": ["training_start_time", "training_end_time", "default_block_duration_minutes"],
        },
        "vocabulary": {"prefix": "general", "fields": ["member_label", "service_label", "training_label"]},
    }

    LDAP_FIELDS = [
        "enabled",
        "server_uri",
        "start_tls",
        "ca_cert_file",
        "ca_cert_content",
        "disable_cert_validation",
        "bind_dn",
        "user_search_base_dn",
        "user_search_filter",
        "group_search_base_dn",
        "group_search_filter",
        "group_type",
        "mirror_groups",
        "require_group",
    ]

    OIDC_FIELDS = [
        "enabled",
        "provider_name",
        "issuer_url",
        "client_id",
        "scope",
        "groups_claim",
        "staff_group",
        "admin_group",
        "require_group_mapping",
        "hide_local_login",
        "trust_provider_mfa",
    ]

    @action(detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated])
    def security(self, request):
        from settings_manager.api.serializers.security_policy import SecurityPolicySerializer
        from settings_manager.models import SecurityPolicy, SettingsWriteLock
        from settings_manager.runtime_policy import POLICY_FIELDS, effective_policy
        from users.step_up import require_step_up

        operation = "view" if request.method == "GET" else "change"
        if not self._check_category_permission(request.user, "security", operation):
            return Response({"detail": "Keine Berechtigung für Sicherheitsrichtlinien."}, status=403)
        if request.method == "GET":
            return Response(effective_policy())
        require_step_up(request)
        with transaction.atomic():
            SettingsWriteLock.objects.get_or_create(category="security")
            SettingsWriteLock.objects.select_for_update().get(category="security")
            current = effective_policy()
            locked = {
                name: "Durch die Umgebung vorgegeben; Änderung nur am Host möglich."
                for name in request.data
                if current["fields"].get(name, {}).get("locked")
            }
            if locked:
                raise drf_serializers.ValidationError(locked)
            merged = {name: current[name] for name in POLICY_FIELDS}
            merged.update(request.data)
            serializer = SecurityPolicySerializer(data=merged)
            serializer.is_valid(raise_exception=True)
            SecurityPolicy.objects.update_or_create(pk=1, defaults=serializer.validated_data)
        return Response(effective_policy())

    @action(detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated])
    def push(self, request):
        from settings_manager.api.serializers.push_configuration import PushConfigurationSerializer
        from settings_manager.models import PushConfiguration, SettingsWriteLock
        from settings_manager.push_configuration import PUSH_FIELDS, effective_push, validate_push
        from users.step_up import require_step_up

        operation = "view" if request.method == "GET" else "change"
        if not self._check_category_permission(request.user, "push", operation):
            return Response({"detail": "Keine Berechtigung für Push-Einstellungen."}, status=403)
        if request.method == "GET":
            return Response(effective_push())
        require_step_up(request)
        with transaction.atomic():
            SettingsWriteLock.objects.get_or_create(category="push")
            SettingsWriteLock.objects.select_for_update().get(category="push")
            current = effective_push(include_secret=True)
            invalid = {
                name: "Unbekanntes oder durch die Umgebung gesperrtes Feld."
                for name in request.data
                if name not in PUSH_FIELDS or current["fields"].get(name, {}).get("locked")
            }
            if invalid:
                raise drf_serializers.ValidationError(invalid)
            serializer = PushConfigurationSerializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            merged = {name: current[name] for name in PUSH_FIELDS}
            merged.update(serializer.validated_data)
            # Host keys are validated by deployment; their legacy activation can still be disabled in the web UI.
            if not any(current["fields"][name]["locked"] for name in ("public_key", "private_key", "subject")):
                validate_push(merged)
            elif merged["enabled"] and not all(merged[name] for name in ("public_key", "private_key", "subject")):
                raise drf_serializers.ValidationError({"enabled": "Die Host-VAPID-Konfiguration ist unvollständig."})
            PushConfiguration.objects.update_or_create(pk=1, defaults=serializer.validated_data)
        return Response(effective_push())

    @action(detail=False, methods=["post"], url_path="push/generate-keys", permission_classes=[IsAuthenticated])
    def generate_push_keys(self, request):
        from settings_manager.models import PushConfiguration, SettingsWriteLock
        from settings_manager.push_configuration import (
            effective_push,
            environment_keys,
            generate_key_pair,
            validate_push,
        )
        from users.step_up import require_step_up

        if not self._check_category_permission(request.user, "push", "change"):
            return Response({"detail": "Keine Berechtigung für Push-Einstellungen."}, status=403)
        require_step_up(request)
        if set(request.data) != {"subject"} or not isinstance(request.data.get("subject"), str):
            raise drf_serializers.ValidationError({"subject": "Eine Kontaktadresse ist erforderlich."})
        with transaction.atomic():
            SettingsWriteLock.objects.get_or_create(category="push")
            SettingsWriteLock.objects.select_for_update().get(category="push")
            if environment_keys() or effective_push()["has_private_key"]:
                raise drf_serializers.ValidationError(
                    {
                        "detail": "Schlüssel sind bereits vorhanden. Vor einer neuen Einrichtung bestehende Konfiguration ausdrücklich entfernen; Geräte müssen anschließend neu angemeldet werden."
                    }
                )
            values = {**generate_key_pair(), "subject": request.data["subject"], "enabled": False}
            validate_push(values)
            PushConfiguration.objects.update_or_create(pk=1, defaults=values)
        return Response(effective_push(), status=201)

    @action(detail=False, methods=["get", "patch"])
    def training(self, request):
        return self._preference_category(request, "training", TrainingSettingsSerializer)

    @action(detail=False, methods=["get", "patch"])
    def vocabulary(self, request):
        return self._preference_category(request, "vocabulary", VocabularySettingsSerializer)

    def _preference_category(self, request, category, serializer_class):
        if not self._check_category_permission(request.user, category, "view" if request.method == "GET" else "change"):
            return Response({"detail": "Keine Berechtigung für diese Einstellungen."}, status=403)
        if request.method == "GET":
            return Response(serializer_class(self._get_category_settings(category)).data)
        return self._patch_preferences(request, category, serializer_class)

    @action(detail=False, methods=["get"])
    def catalog(self, request):
        from settings_manager.configuration_catalog import configuration_catalog

        categories = [name for name in self.CATEGORY_MAPPINGS if self._check_category_permission(request.user, name)]
        if not categories:
            return Response({"detail": "Keine Berechtigung für Einstellungen."}, status=403)
        return Response(configuration_catalog(self, request, categories))

    @action(detail=False, methods=["get"])
    def setup(self, request):
        from settings_manager.configuration_catalog import setup_status

        if not self._check_category_permission(request.user, "all", "view"):
            return Response({"detail": "Die Einrichtung ist der Systemadministration vorbehalten."}, status=403)
        return Response(setup_status(self))

    @action(detail=False, methods=["get"])
    def operations(self, request):
        """Read-only host status written by jfctl (OPS-03.4); system administration only."""
        from settings_manager.operations_status import operations_status

        if not self._check_category_permission(request.user, "all", "view"):
            return Response({"detail": "Der Betriebsstatus ist der Systemadministration vorbehalten."}, status=403)
        return Response(operations_status())

    @action(detail=False, methods=["get"], url_path="client-defaults")
    def client_defaults(self, request):
        from jf_manager_backend.api_views import AppSettingsView

        return AppSettingsView().get(request)

    @action(detail=False, methods=["post"], url_path="email/test-connection")
    def email_test_connection(self, request):
        return self._test_smtp(request, send=False)

    @action(detail=False, methods=["post"], url_path="email/send-test")
    def email_send_test(self, request):
        return self._test_smtp(request, send=True)

    def _test_smtp(self, request, send):
        from django.core.mail import EmailMessage

        from jf_manager_backend.email_backend import ConfiguredSMTPBackend
        from users.step_up import require_step_up

        if not self._check_category_permission(request.user, "email", "change"):
            return Response({"detail": "Keine Berechtigung für E-Mail-Verbindungstests."}, status=403)
        require_step_up(request)
        if set(request.data) != ({"recipient", "confirm_send"} if send else set()):
            raise drf_serializers.ValidationError({"detail": "Ungültige Testparameter."})
        recipient = None
        if send:
            if request.data["confirm_send"] is not True:
                raise drf_serializers.ValidationError({"confirm_send": "Testversand ausdrücklich bestätigen."})
            recipient = drf_serializers.EmailField().run_validation(request.data["recipient"])
        connection = ConfiguredSMTPBackend(fail_silently=False, timeout=5)
        try:
            connection.open()
            if send:
                preferences = global_preferences_registry.manager()
                message = EmailMessage(
                    subject="JF Manager: SMTP-Test",
                    body="Diese E-Mail bestätigt den ausdrücklich angeforderten Testversand.",
                    from_email=preferences["email__default_from_email"],
                    to=[recipient],
                    connection=connection,
                )
                if message.send(fail_silently=False) != 1:
                    raise ImproperlyConfigured("Testversand fehlgeschlagen.")
            return Response(
                {
                    "ok": True,
                    "detail": "Test-E-Mail gesendet." if send else "Verbindung erfolgreich; keine E-Mail gesendet.",
                }
            )
        except Exception:
            # Provider errors may include identities or secrets. Return no raw exception.
            return Response(
                {
                    "ok": False,
                    "detail": "SMTP-Test fehlgeschlagen. Gespeicherte Server-/TLS-Einstellungen und Zugangsdaten prüfen.",
                },
                status=400,
            )
        finally:
            with suppress(Exception):
                connection.close()

    def _get_category_settings(self, category, tolerate_email_secret_error=False):
        """Helper to retrieve settings for a specific category"""
        mapping = self.CATEGORY_MAPPINGS.get(category)

        if not mapping:
            return None

        settings = {}
        prefix = mapping["prefix"]

        from dynamic_preferences.models import GlobalPreferenceModel

        for field in mapping["fields"]:
            preference = global_preferences_registry.get(section=prefix, name=field)
            row = GlobalPreferenceModel.objects.filter(section=prefix, name=field).first()
            try:
                settings[field] = preference.serializer.deserialize(row.raw_value) if row else preference.default
            except ImproperlyConfigured:
                if not (tolerate_email_secret_error and category == "email" and field == "email_host_password"):
                    raise
                settings["email_credentials_unavailable"] = True
                settings["has_email_host_password"] = True
        if category == "email":
            settings.setdefault("has_email_host_password", bool(settings.get("email_host_password")))
            settings.setdefault("email_credentials_unavailable", False)
        return settings

    def _save_category_settings(self, category, data):
        from dynamic_preferences.models import GlobalPreferenceModel

        prefix = self.CATEGORY_MAPPINGS[category]["prefix"]
        manager = global_preferences_registry.manager()
        for field, value in data.items():
            if field not in self.CATEGORY_MAPPINGS[category]["fields"]:
                continue
            if hasattr(value, "strftime"):
                value = value.strftime("%H:%M")
            preference = global_preferences_registry.get(section=prefix, name=field)
            raw_value = preference.serializer.serialize(value)
            GlobalPreferenceModel.objects.bulk_create(
                [GlobalPreferenceModel(section=prefix, name=field, raw_value=raw_value)], ignore_conflicts=True
            )
            GlobalPreferenceModel.objects.filter(section=prefix, name=field).update(raw_value=raw_value)
            cache_key = manager.get_cache_key(prefix, field)
            transaction.on_commit(lambda key=cache_key: manager.cache.delete(key))
        return True

    def _patch_preferences(self, request, category, serializer_class):
        from settings_manager.models import SettingsWriteLock

        with transaction.atomic():
            SettingsWriteLock.objects.get_or_create(category=category)
            SettingsWriteLock.objects.select_for_update().get(category=category)
            writable = {name for name, field in serializer_class().fields.items() if not field.read_only}
            unknown = set(request.data) - writable
            if unknown:
                raise drf_serializers.ValidationError(
                    {name: "Unbekanntes oder schreibgeschütztes Feld." for name in unknown}
                )
            current = self._get_category_settings(category, tolerate_email_secret_error=True)
            merged = {name: value for name, value in current.items() if name in writable}
            merged.update(request.data)
            serializer = serializer_class(data=merged)
            serializer.is_valid(raise_exception=True)
            self._save_category_settings(category, {name: serializer.validated_data[name] for name in request.data})
            # Never let a failed write populate preference caches with partial state.
            result = self._get_category_settings(category, tolerate_email_secret_error=True)
        return Response(serializer_class(result).data)

    def _check_category_permission(self, user, category, permission_type="view"):
        """Check if user has permission for a specific category"""
        # is_staff only controls Django admin access, never settings rights.
        if user.is_superuser:
            return True

        # Training defaults and vocabulary belong to general organisation configuration.
        if category in {"training", "vocabulary"}:
            category = "general"
        # Check specific permission
        permission = f"settings_manager.{permission_type}_{category}_settings"
        if user.has_perm(permission):
            return True

        # Check global permission
        global_permission = f"settings_manager.{permission_type}_all_settings"
        return bool(user.has_perm(global_permission))

    def _get_ldap_settings(self):
        config = LDAPConfig.get_or_create_default()
        settings = {field: getattr(config, field) for field in self.LDAP_FIELDS}
        settings["has_bind_password"] = bool(config.bind_password)
        return settings

    def _save_ldap_settings(self, data):
        config = LDAPConfig.get_or_create_default()
        for field in self.LDAP_FIELDS:
            if field in data:
                setattr(config, field, data[field])

        if "bind_password" in data:
            config.bind_password = data["bind_password"]

        config.save()
        return config

    def _get_oidc_settings(self, request=None):
        config = OIDCConfig.get_or_create_default()
        settings = {field: getattr(config, field) for field in self.OIDC_FIELDS}
        settings["has_client_secret"] = bool(config.client_secret)
        if request is not None:
            settings["callback_url"] = request.build_absolute_uri("/api/v1/auth/oidc/callback/")
        return settings

    def _save_oidc_settings(self, data):
        config = OIDCConfig.get_or_create_default()
        for field in self.OIDC_FIELDS:
            if field in data:
                setattr(config, field, data[field])

        if "client_secret" in data:
            config.client_secret = data["client_secret"]

        config.save()
        return config

    def _patch_model_settings(self, request, category, serializer_class):
        from settings_manager.models import SettingsWriteLock

        writable = {name for name, field in serializer_class().fields.items() if not field.read_only}
        unknown = set(request.data) - writable
        if unknown:
            raise drf_serializers.ValidationError(
                {name: "Unbekanntes oder schreibgeschütztes Feld." for name in unknown}
            )
        model = LDAPConfig if category == "ldap" else OIDCConfig
        with transaction.atomic():
            SettingsWriteLock.objects.get_or_create(category=category)
            SettingsWriteLock.objects.select_for_update().get(category=category)
            config = model.get_or_create_default()
            merged = {name: getattr(config, name) for name in writable}
            merged.update(request.data)
            serializer = serializer_class(data=merged)
            serializer.is_valid(raise_exception=True)
            for name in request.data:
                setattr(config, name, serializer.validated_data[name])
            try:
                config.save()
            except ValidationError as exc:
                raise drf_serializers.ValidationError(
                    exc.message_dict if hasattr(exc, "message_dict") else exc.messages
                ) from exc
            result = self._get_ldap_settings() if category == "ldap" else self._get_oidc_settings(request)
        return Response(serializer_class(result).data)

    @extend_schema(
        summary="List all settings",
        description="Get all application settings grouped by category. Only returns categories the user has permission to view.",
        responses={200: AllSettingsSerializer},
    )
    def list(self, request):
        """GET /api/v1/settings/ - List all settings"""
        # Check if user has permission to view all settings
        if not any(
            self._check_category_permission(request.user, category, "view") for category in self.CATEGORY_MAPPINGS
        ):
            return Response(
                {"detail": "You do not have permission to view settings."}, status=status.HTTP_403_FORBIDDEN
            )

        all_settings = {}

        # Get settings for each category the user can access
        for category in self.CATEGORY_MAPPINGS:
            if self._check_category_permission(request.user, category, "view"):
                if category == "push":
                    from settings_manager.push_configuration import effective_push

                    category_settings = effective_push()
                elif category == "security":
                    from settings_manager.runtime_policy import effective_policy

                    category_settings = effective_policy()
                elif category == "ldap":
                    category_settings = self._get_ldap_settings()
                elif category == "oidc":
                    category_settings = self._get_oidc_settings()
                else:
                    category_settings = self._get_category_settings(category, tolerate_email_secret_error=True)
                if category_settings is not None:
                    all_settings[category] = category_settings

        serializer = AllSettingsSerializer(all_settings)
        return Response(serializer.data)

    @extend_schema(
        summary="Get general settings",
        description="Get general application settings",
        responses={200: GeneralSettingsSerializer},
    )
    @action(detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated])
    def general(self, request):
        """GET/PATCH /api/v1/settings/general/"""
        if request.method == "GET":
            if not self._check_category_permission(request.user, "general", "view"):
                return Response(
                    {"detail": "You do not have permission to view general settings."}, status=status.HTTP_403_FORBIDDEN
                )

            settings = self._get_category_settings("general")
            serializer = GeneralSettingsSerializer(settings)
            return Response(serializer.data)

        else:  # PATCH
            if not self._check_category_permission(request.user, "general", "change"):
                return Response(
                    {"detail": "You do not have permission to change general settings."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            return self._patch_preferences(request, "general", GeneralSettingsSerializer)

    @extend_schema(
        summary="Get email settings",
        description="Get email/SMTP configuration settings",
        responses={200: EmailSettingsSerializer},
    )
    @action(detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated, StepUpForWrites])
    def email(self, request):
        """GET/PATCH /api/v1/settings/email/"""
        if request.method == "GET":
            if not self._check_category_permission(request.user, "email", "view"):
                return Response(
                    {"detail": "You do not have permission to view email settings."}, status=status.HTTP_403_FORBIDDEN
                )

            settings = self._get_category_settings("email", tolerate_email_secret_error=True)
            serializer = EmailSettingsSerializer(settings)
            return Response(serializer.data)

        else:  # PATCH
            if not self._check_category_permission(request.user, "email", "change"):
                return Response(
                    {"detail": "You do not have permission to change email settings."}, status=status.HTTP_403_FORBIDDEN
                )

            from users.step_up import require_step_up

            require_step_up(request)
            return self._patch_preferences(request, "email", EmailSettingsSerializer)

    @extend_schema(
        summary="Get member settings",
        description="Get member-related settings (absence alerts, etc.)",
        responses={200: MemberSettingsSerializer},
    )
    @action(detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated])
    def member(self, request):
        """GET/PATCH /api/v1/settings/member/"""
        if request.method == "GET":
            if not self._check_category_permission(request.user, "member", "view"):
                return Response(
                    {"detail": "You do not have permission to view member settings."}, status=status.HTTP_403_FORBIDDEN
                )

            settings = self._get_category_settings("member")
            serializer = MemberSettingsSerializer(settings)
            return Response(serializer.data)

        else:  # PATCH
            if not self._check_category_permission(request.user, "member", "change"):
                return Response(
                    {"detail": "You do not have permission to change member settings."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            return self._patch_preferences(request, "member", MemberSettingsSerializer)

    @extend_schema(
        summary="Get service settings",
        description="Get service-related settings (default times, etc.)",
        responses={200: ServiceSettingsSerializer},
    )
    @action(detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated])
    def service(self, request):
        """GET/PATCH /api/v1/settings/service/"""
        if request.method == "GET":
            if not self._check_category_permission(request.user, "service", "view"):
                return Response(
                    {"detail": "You do not have permission to view service settings."}, status=status.HTTP_403_FORBIDDEN
                )

            settings = self._get_category_settings("service")
            serializer = ServiceSettingsSerializer(settings)
            return Response(serializer.data)

        else:  # PATCH
            if not self._check_category_permission(request.user, "service", "change"):
                return Response(
                    {"detail": "You do not have permission to change service settings."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            return self._patch_preferences(request, "service", ServiceSettingsSerializer)

    @extend_schema(
        summary="Get order settings",
        description="Get order-related settings (equipment manager email, etc.)",
        responses={200: OrderSettingsSerializer},
    )
    @action(detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated])
    def order(self, request):
        """GET/PATCH /api/v1/settings/order/"""
        if request.method == "GET":
            if not self._check_category_permission(request.user, "order", "view"):
                return Response(
                    {"detail": "You do not have permission to view order settings."}, status=status.HTTP_403_FORBIDDEN
                )

            settings = self._get_category_settings("order")
            serializer = OrderSettingsSerializer(settings)
            return Response(serializer.data)

        else:  # PATCH
            if not self._check_category_permission(request.user, "order", "change"):
                return Response(
                    {"detail": "You do not have permission to change order settings."}, status=status.HTTP_403_FORBIDDEN
                )

            return self._patch_preferences(request, "order", OrderSettingsSerializer)

    @extend_schema(
        summary="Get LDAP settings",
        description="Get LDAP authentication and group sync configuration",
        responses={200: LDAPSettingsSerializer},
    )
    @action(detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated, StepUpForWrites])
    def ldap(self, request):
        """GET/PATCH /api/v1/settings/ldap/"""
        if request.method == "GET":
            if not self._check_category_permission(request.user, "ldap", "view"):
                return Response(
                    {"detail": "You do not have permission to view LDAP settings."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            serializer = LDAPSettingsSerializer(self._get_ldap_settings())
            return Response(serializer.data)

        if not self._check_category_permission(request.user, "ldap", "change"):
            return Response(
                {"detail": "You do not have permission to change LDAP settings."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return self._patch_model_settings(request, "ldap", LDAPSettingsSerializer)

    @extend_schema(
        summary="Test LDAP connection",
        description="Test LDAP server bind and configured user/group search bases",
        responses={200: LDAPConnectionTestSerializer, 400: LDAPConnectionTestSerializer},
    )
    @action(detail=False, methods=["post"], url_path="ldap/test-connection", permission_classes=[IsAuthenticated])
    def ldap_test_connection(self, request):
        """POST /api/v1/settings/ldap/test-connection/"""
        if not self._check_category_permission(request.user, "ldap", "change"):
            return Response(
                {"detail": "You do not have permission to test LDAP settings."},
                status=status.HTTP_403_FORBIDDEN,
            )

        config = LDAPConfig.get_or_create_default()
        if not config.server_uri:
            return Response(
                {"ok": False, "detail": "LDAP server URI is not configured."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            import ldap

            apply_ldap_tls_options(config)
            connection = ldap.initialize(config.server_uri)
            connection.set_option(ldap.OPT_NETWORK_TIMEOUT, 5)

            if config.start_tls:
                connection.start_tls_s()

            if config.bind_dn:
                connection.simple_bind_s(config.bind_dn, config.bind_password or "")
            else:
                connection.simple_bind_s()

            if config.user_search_base_dn and config.user_search_filter:
                connection.search_s(config.user_search_base_dn, ldap.SCOPE_SUBTREE, config.user_search_filter)

            if config.group_search_base_dn and config.group_search_filter:
                connection.search_s(config.group_search_base_dn, ldap.SCOPE_SUBTREE, config.group_search_filter)

            connection.unbind_s()
            return Response({"ok": True, "detail": "LDAP connection test succeeded."})
        except Exception:
            return Response(
                {"ok": False, "detail": "LDAP-Verbindung fehlgeschlagen; Server, Zertifikat und Zugangsdaten prüfen."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @extend_schema(
        summary="Browse LDAP directory",
        description=(
            "Browse the LDAP directory at a given base DN using the saved server credentials. "
            "Returns up to 200 entries with their DN and requested attributes."
        ),
    )
    @action(detail=False, methods=["post"], url_path="ldap/browse", permission_classes=[IsAuthenticated])
    def ldap_browse(self, request):
        """POST /api/v1/settings/ldap/browse/"""
        if not request.user.is_superuser:
            return Response(
                {"detail": "Keine Berechtigung für LDAP-Einstellungen."},
                status=status.HTTP_403_FORBIDDEN,
            )

        config = LDAPConfig.get_or_create_default()
        if not config.server_uri:
            return Response(
                {"ok": False, "detail": "LDAP Server URI ist nicht konfiguriert.", "entries": []},
                status=status.HTTP_400_BAD_REQUEST,
            )

        base_dn = request.data.get("base_dn", "")
        filter_str = request.data.get("filter", "(objectClass=*)")
        scope_str = request.data.get("scope", "one")
        requested_attrs = request.data.get("attributes", ["cn", "ou", "description", "objectClass"])

        # Restrict scope to known safe values
        if scope_str not in ("one", "sub"):
            scope_str = "one"

        # Guard against LDAP filter injection: cap length and allow only safe characters
        import re

        if len(filter_str) > 512 or not re.fullmatch(r"[\w\s=*()\-.,@:/\\+<>\"'#;!%&|~]+", filter_str):
            return Response(
                {"ok": False, "detail": "Ungültiger LDAP-Filter.", "entries": []},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            import ldap

            apply_ldap_tls_options(config)
            conn = ldap.initialize(config.server_uri)
            conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 5)

            if config.start_tls:
                conn.start_tls_s()

            if config.bind_dn:
                conn.simple_bind_s(config.bind_dn, config.bind_password or "")
            else:
                conn.simple_bind_s()

            scope = ldap.SCOPE_ONELEVEL if scope_str == "one" else ldap.SCOPE_SUBTREE
            raw_results = conn.search_s(base_dn, scope, filter_str, requested_attrs)
            conn.unbind_s()

            entries = []
            for dn, attrs_dict in raw_results:
                if dn is None:
                    continue
                entry: dict = {"dn": dn}
                for attr_name, values in attrs_dict.items():
                    decoded = []
                    for v in values if isinstance(values, list) else [values]:
                        if isinstance(v, bytes):
                            try:
                                decoded.append(v.decode("utf-8"))
                            except Exception:
                                decoded.append(v.hex())
                        else:
                            decoded.append(str(v))
                    entry[attr_name] = decoded[0] if len(decoded) == 1 else decoded
                entries.append(entry)

            return Response({"ok": True, "entries": entries, "total": len(entries)})
        except Exception:
            return Response(
                {
                    "ok": False,
                    "detail": "Verzeichnisabfrage fehlgeschlagen; Server, Zertifikat und Zugangsdaten prüfen.",
                    "entries": [],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @extend_schema(
        summary="Get OIDC settings",
        description="Get OpenID Connect authentication configuration",
        responses={200: OIDCSettingsSerializer},
    )
    @action(detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated, StepUpForWrites])
    def oidc(self, request):
        """GET/PATCH /api/v1/settings/oidc/"""
        if request.method == "GET":
            if not self._check_category_permission(request.user, "oidc", "view"):
                return Response(
                    {"detail": "You do not have permission to view OIDC settings."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            serializer = OIDCSettingsSerializer(self._get_oidc_settings(request))
            return Response(serializer.data)

        if not self._check_category_permission(request.user, "oidc", "change"):
            return Response(
                {"detail": "You do not have permission to change OIDC settings."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return self._patch_model_settings(request, "oidc", OIDCSettingsSerializer)

    @extend_schema(
        summary="Test OIDC discovery",
        description="Test whether the OIDC Discovery Document can be fetched from the given issuer URL",
        responses={200: OIDCDiscoveryResultSerializer},
    )
    @action(detail=False, methods=["post"], url_path="oidc/test-discovery", permission_classes=[IsAuthenticated])
    def oidc_test_discovery(self, request):
        """POST /api/v1/settings/oidc/test-discovery/"""
        if not self._check_category_permission(request.user, "oidc", "change"):
            return Response(
                {"detail": "You do not have permission to test OIDC settings."},
                status=status.HTTP_403_FORBIDDEN,
            )

        from users.oidc_views import OIDCTestDiscoveryView

        # Delegate to the reusable view logic
        view = OIDCTestDiscoveryView()
        view.request = request
        return view.post(request)

    @extend_schema(
        summary="Get user permissions",
        description="Get current user's permissions for viewing and changing settings",
        responses={200: UserPermissionsSerializer},
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def permissions(self, request):
        """GET /api/v1/settings/permissions/"""
        user = request.user

        permissions_data = {
            "can_view_all": user.is_superuser or user.has_perm("settings_manager.view_all_settings"),
            "can_change_all": user.is_superuser or user.has_perm("settings_manager.change_all_settings"),
            "categories": {},
        }

        # Check permissions for each category
        for category in self.CATEGORY_MAPPINGS:
            permissions_data["categories"][category] = {
                "can_view": self._check_category_permission(user, category, "view"),
                "can_change": self._check_category_permission(user, category, "change"),
            }

        serializer = UserPermissionsSerializer(permissions_data)
        return Response(serializer.data)
