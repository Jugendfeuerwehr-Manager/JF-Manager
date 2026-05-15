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

from mozilla_django_oidc.auth import OIDCAuthenticationBackend

logger = logging.getLogger("users.oidc_backend")


class JFManagerOIDCBackend(OIDCAuthenticationBackend):
    """
    Runtime-configurable OIDC backend for JF-Manager.

    Returns None from authenticate() when OIDC is disabled so Django falls
    through to the next backend (ModelBackend / local login).
    """

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
        """
        Find existing user by email first (case-insensitive), then by sub claim.
        """
        email = claims.get("email", "").strip()
        if email:
            users = self.UserModel.objects.filter(email__iexact=email)
            if users.exists():
                logger.debug("OIDC: found existing user by email '%s'", email)
                return users

        # Fall back to sub claim stored as username
        sub = claims.get("sub", "")
        if sub:
            users = self.UserModel.objects.filter(username=sub)
            if users.exists():
                logger.debug("OIDC: found existing user by sub '%s'", sub)
                return users

        logger.debug("OIDC: no existing user found for email='%s' sub='%s'", email, sub)
        return self.UserModel.objects.none()

    # ---------------------------------------------------------------------------
    # User creation / update
    # ---------------------------------------------------------------------------

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
        user.first_name = claims.get("given_name", claims.get("first_name", user.first_name)) or user.first_name
        user.last_name = claims.get("family_name", claims.get("last_name", user.last_name)) or user.last_name
        email = claims.get("email", "").strip()
        if email:
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
        """
        Sync UserDepartmentRole records from OIDCGroupMapping after login.
        Mirrors ConfigurableLDAPBackend._sync_department_roles().
        """
        import contextlib

        from departments.models import UserDepartmentRole
        from settings_manager.models import OIDCGroupMapping

        mappings = list(
            OIDCGroupMapping.objects.filter(oidc_config=config)
            .select_related("department")
            .prefetch_related("auth_groups")
        )

        if not mappings:
            logger.debug("OIDC: no group mappings configured — skipping department role sync")
            return

        logger.debug(
            "OIDC: syncing %d group mapping(s) for user '%s' (groups=%s)",
            len(mappings),
            user.username,
            groups,
        )

        for mapping in mappings:
            is_member = mapping.group_claim_value in groups

            if is_member and mapping.department:
                role, created = UserDepartmentRole.objects.get_or_create(user=user, department=mapping.department)
                existing_ids = set(role.groups.values_list("id", flat=True))
                mapped_ids = set(mapping.auth_groups.values_list("id", flat=True))
                role.groups.set(list(existing_ids | mapped_ids))

                if created:
                    logger.info(
                        "OIDC: created UserDepartmentRole for user '%s' in department '%s'",
                        user.username,
                        mapping.department,
                    )
                else:
                    logger.debug(
                        "OIDC: updated UserDepartmentRole for user '%s' in department '%s'",
                        user.username,
                        mapping.department,
                    )

            elif not is_member and mapping.revoke_on_mismatch and mapping.department:
                with contextlib.suppress(UserDepartmentRole.DoesNotExist):
                    deleted_count, _ = UserDepartmentRole.objects.filter(
                        user=user, department=mapping.department
                    ).delete()
                    if deleted_count:
                        logger.info(
                            "OIDC: revoked UserDepartmentRole for user '%s' in department '%s' "
                            "(revoke_on_mismatch=True)",
                            user.username,
                            mapping.department,
                        )
