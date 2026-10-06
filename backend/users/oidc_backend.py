"""
JF-Manager OIDC Authentication Backend

Subclasses mozilla_django_oidc.auth.OIDCAuthenticationBackend to:
- Read OIDC configuration from the DB (OIDCConfig) at runtime instead of
  static django.conf.settings — same pattern as ConfigurableLDAPBackend.
- Auto-create / update users from OIDC claims.
- Sync is_staff / is_superuser based on configured staff_group / admin_group.
- Sync UserDepartmentRole records from OIDCGroupMapping (mirrors ldap_backend).
- Block login via require_group_mapping when no mapping matches.
"""

import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

logger = logging.getLogger("users.oidc_backend")


class JFManagerOIDCBackend(OIDCAuthenticationBackend):
    """
    Runtime-configurable OIDC backend for JF-Manager.

    Returns None from authenticate() when OIDC is disabled so Django falls
    through to the next backend (ModelBackend / local login).
    """

    def __init__(self, *args, **kwargs):
        # Django instantiates every backend for each permission check. Provider
        # settings, including the encrypted client secret, are read only while a
        # login is actually processed (get_settings), never eagerly here.
        self.UserModel = get_user_model()

    # ---------------------------------------------------------------------------
    # Config helpers
    # ---------------------------------------------------------------------------

    def _get_config(self):
        from settings_manager.models import OIDCConfig

        return OIDCConfig.get_or_create_default()

    def get_settings(self, attr, *args):
        """
        Override to read OIDC provider settings from DB instead of
        django.conf.settings.  Falls back to super() for non-provider settings
        (e.g. OIDC_VERIFY_SSL, OIDC_TIMEOUT, etc.).
        """
        config = self._get_config()

        db_map = {
            "OIDC_RP_CLIENT_ID": config.client_id,
            "OIDC_RP_CLIENT_SECRET": config.client_secret,
            "OIDC_RP_SCOPES": config.scope,
        }

        if attr in db_map:
            value = db_map[attr]
            if value:
                return value
            if args:
                return args[0]
            return super().get_settings(attr, *args)

        return super().get_settings(attr, *args)

    # ---------------------------------------------------------------------------
    # Enable / disable guard
    # ---------------------------------------------------------------------------

    def authenticate(self, request, **kwargs):
        # Only the OIDC callback supplies verified claims; password logins pass
        # through without touching the OIDC configuration or its secret.
        if not getattr(request, "_oidc_claims", None):
            return None
        config = self._get_config()
        if not config or not config.enabled:
            logger.debug("OIDC is disabled — skipping JFManagerOIDCBackend")
            return None

        if not config.issuer_url or not config.client_id:
            logger.warning("OIDC enabled but issuer_url or client_id is not configured — skipping")
            return None

        # OIDCCallbackView manually exchanges the authorization code, verifies the
        # id_token, and stores the decoded claims on the request.  We read them
        # here instead of calling super().authenticate() which would try to
        # re-exchange the already-consumed code (and needs URL patterns from
        # mozilla_django_oidc that we deliberately do not include).
        claims = getattr(request, "_oidc_claims", None)
        if not claims:
            logger.debug("OIDC authenticate(): no pre-decoded claims on request — skipping")
            return None

        logger.debug("OIDC authenticate() from pre-decoded claims (provider '%s')", config.provider_name)

        if not self.verify_claims(claims):
            logger.warning("OIDC: verify_claims() rejected the token claims")
            return None

        users = self.filter_users_by_claims(claims)
        if users.exists():
            return self.update_user(users.first(), claims)
        return self.create_user(claims)

    # ---------------------------------------------------------------------------
    # Discovery document — provide endpoints from DB config
    # ---------------------------------------------------------------------------

    # (get_settings() reads self._discovery_doc set by OIDCCallbackView; no
    #  override of get_userinfo() needed since we do not call the userinfo
    #  endpoint — claims come from the id_token directly.)

    # ---------------------------------------------------------------------------
    # User lookup
    # ---------------------------------------------------------------------------

    def filter_users_by_claims(self, claims):
        """Identify accounts by the stable issuer/subject pair.

        Never auto-link local/LDAP accounts or match a provider-controlled subject
        to a local username: either would let the provider take over that account.
        """
        from django.core.exceptions import PermissionDenied

        issuer = claims.get("iss", "").rstrip("/")
        subject = claims.get("sub", "")
        if not issuer or not subject:
            raise PermissionDenied("OIDC-Identität fehlt.")
        bound = self.UserModel.objects.filter(oidc_issuer=issuer, oidc_subject=subject, auth_source="oidc")
        if bound.exists():
            return bound
        email = claims.get("email", "").strip()
        if not email or claims.get("email_verified") is not True:
            raise PermissionDenied("Der OIDC-Anbieter muss eine bestätigte E-Mail-Adresse liefern.")
        users = self.UserModel.objects.filter(email__iexact=email)
        if users.exists():
            raise PermissionDenied("Ein vorhandenes Konto darf nicht automatisch mit OIDC verknüpft werden.")
        return users

    # ---------------------------------------------------------------------------
    # User creation / update
    # ---------------------------------------------------------------------------

    @transaction.atomic
    def create_user(self, claims):
        config = self._get_config()
        email = claims.get("email", "").strip()
        groups = self._extract_groups(claims, config)

        self._check_require_group_mapping(groups, config)

        # Generate a clean username: prefer preferred_username, fall back to sub
        username = claims.get("preferred_username", "") or claims.get("sub", "") or email
        # Ensure username uniqueness (max 150 chars)
        username = username[:150]

        user = self.UserModel.objects.create_user(username=username, email=email)
        user.auth_source = "oidc"
        user.save(update_fields=["auth_source"])
        self._apply_claims(user, claims, groups, config)

        logger.info(
            "OIDC: created new user '%s' (email='%s') via provider '%s'",
            user.username,
            email,
            config.provider_name,
        )
        return user

    def update_user(self, user, claims):
        config = self._get_config()
        groups = self._extract_groups(claims, config)

        self._check_require_group_mapping(groups, config)
        self._apply_claims(user, claims, groups, config)

        if user.auth_source != "oidc":
            user.auth_source = "oidc"
            user.save(update_fields=["auth_source"])

        logger.debug(
            "OIDC: updated user '%s' from claims (provider '%s')",
            user.username,
            config.provider_name,
        )
        return user

    # ---------------------------------------------------------------------------
    # Claim verification
    # ---------------------------------------------------------------------------

    def verify_claims(self, claims):
        verified = super().verify_claims(claims)
        if not verified:
            return False
        config = self._get_config()
        if not config.require_group_mapping:
            return True
        groups = self._extract_groups(claims, config)
        return self._has_any_group_mapping(groups, config)

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    def _extract_groups(self, claims, config):
        """Extract the list of group values from the claims using groups_claim."""
        raw = claims.get(config.groups_claim, [])
        if isinstance(raw, str):
            # Some providers send comma-separated string
            raw = [g.strip() for g in raw.split(",") if g.strip()]
        return list(raw) if raw else []

    def _apply_claims(self, user, claims, groups, config):
        """Apply name, email, staff/superuser flags and group mappings to user."""
        # Persist provider identity; subsequent logins no longer depend on mutable email.
        user.oidc_issuer = claims.get("iss", "").rstrip("/")
        user.oidc_subject = claims.get("sub", "")
        user.first_name = claims.get("given_name", claims.get("first_name", user.first_name)) or user.first_name
        user.last_name = claims.get("family_name", claims.get("last_name", user.last_name)) or user.last_name
        email = claims.get("email", "").strip()
        if email and claims.get("email_verified") is True:
            user.email = email

        # Staff / superuser flags from group membership
        if config.staff_group:
            new_staff = config.staff_group in groups
            if user.is_staff != new_staff:
                logger.info(
                    "OIDC: setting is_staff=%s for user '%s' (group '%s')",
                    new_staff,
                    user.username,
                    config.staff_group,
                )
            user.is_staff = new_staff

        if config.admin_group:
            new_admin = config.admin_group in groups
            if user.is_superuser != new_admin:
                logger.info(
                    "OIDC: setting is_superuser=%s for user '%s' (group '%s')",
                    new_admin,
                    user.username,
                    config.admin_group,
                )
            user.is_superuser = new_admin

        user.save()
        self._sync_group_mappings(user, groups, config)

    def _has_any_group_mapping(self, groups, config):
        """Check if at least one OIDCGroupMapping matches the user's groups."""
        from settings_manager.models import OIDCGroupMapping

        return OIDCGroupMapping.objects.filter(
            oidc_config=config,
            group_claim_value__in=groups,
        ).exists()

    def _check_require_group_mapping(self, groups, config):
        """Raise SuspiciousOperation if require_group_mapping is on and no mapping matches."""
        from django.core.exceptions import SuspiciousOperation

        if config.require_group_mapping and not self._has_any_group_mapping(groups, config):
            logger.warning(
                "OIDC: login blocked for user — require_group_mapping=True and no mapping found "
                "(groups=%s, provider='%s')",
                groups,
                config.provider_name,
            )
            raise SuspiciousOperation(
                "Dein Account ist keiner Abteilung zugeordnet. Bitte wende dich an einen Administrator."
            )

    def _sync_group_mappings(self, user, groups, config):
        """Project independently owned OIDC grants after verified login."""
        from departments.assignment_sources import sync_external_groups
        from settings_manager.models import OIDCGroupMapping

        mappings = list(
            OIDCGroupMapping.objects.filter(oidc_config=config)
            .select_related("department")
            .prefetch_related("auth_groups__role_template")
        )
        sync_external_groups(user, "oidc", mappings, lambda mapping: mapping.group_claim_value in groups)
