import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django_auth_ldap.backend import LDAPBackend
from django_auth_ldap.config import ActiveDirectoryGroupType, GroupOfNamesType, LDAPSearch

from settings_manager.models import LDAPConfig
from users.ldap_tls import apply_ldap_tls_options

logger = logging.getLogger("users.ldap_backend")


def _set_setting(name, value):
    setattr(settings, name, value)


class ConfigurableLDAPBackend(LDAPBackend):
    """
    LDAP backend that reads runtime configuration from LDAPConfig.
    Returns None when LDAP is disabled/misconfigured so Django can fall back to
    ModelBackend for local accounts.
    """

    def _active_config(self):
        # The bind password is decrypted only once LDAP is known to be enabled.
        return LDAPConfig.objects.order_by("id").defer("bind_password").first()

    def _configure_runtime(self):
        config = self._active_config()
        if not config or not config.enabled:
            return False

        if not config.server_uri or not config.user_search_base_dn or not config.user_search_filter:
            return False

        try:
            bind_password = config.bind_password or ""
        except ImproperlyConfigured:
            # Fail closed for LDAP only; local accounts must still be able to sign in.
            logger.error("LDAP-Anmeldung deaktiviert: Bind-Passwort ist mit dem Schlüsselring nicht lesbar.")
            return False

        try:
            import ldap
        except Exception:
            return False

        try:
            apply_ldap_tls_options(config)
        except Exception:
            return False

        _set_setting("AUTH_LDAP_SERVER_URI", config.server_uri)
        _set_setting("AUTH_LDAP_START_TLS", config.start_tls)
        _set_setting("AUTH_LDAP_BIND_DN", config.bind_dn)
        _set_setting("AUTH_LDAP_BIND_PASSWORD", bind_password)
        _set_setting("AUTH_LDAP_ALWAYS_UPDATE_USER", True)

        _set_setting(
            "AUTH_LDAP_USER_SEARCH",
            LDAPSearch(config.user_search_base_dn, ldap.SCOPE_SUBTREE, config.user_search_filter),
        )

        if config.group_search_base_dn:
            _set_setting(
                "AUTH_LDAP_GROUP_SEARCH",
                LDAPSearch(config.group_search_base_dn, ldap.SCOPE_SUBTREE, config.group_search_filter),
            )
            if config.group_type == LDAPConfig.GroupType.ACTIVE_DIRECTORY:
                _set_setting("AUTH_LDAP_GROUP_TYPE", ActiveDirectoryGroupType())
            else:
                _set_setting("AUTH_LDAP_GROUP_TYPE", GroupOfNamesType())

            _set_setting("AUTH_LDAP_MIRROR_GROUPS", False)  # ROLE-02: explicit mappings preserve local roles
            _set_setting("AUTH_LDAP_REQUIRE_GROUP", config.require_group or None)
        else:
            _set_setting("AUTH_LDAP_GROUP_SEARCH", None)
            _set_setting("AUTH_LDAP_GROUP_TYPE", None)
            _set_setting("AUTH_LDAP_MIRROR_GROUPS", False)
            _set_setting("AUTH_LDAP_REQUIRE_GROUP", None)

        return True

    def authenticate(self, request, username=None, password=None, **kwargs):
        import contextlib

        if not self._configure_runtime():
            return None
        user = super().authenticate(request, username=username, password=password, **kwargs)
        if user is not None:
            with contextlib.suppress(Exception):
                self._sync_department_roles(user)
            with contextlib.suppress(Exception):
                if user.auth_source != "ldap":
                    user.auth_source = "ldap"
                    user.save(update_fields=["auth_source"])
        return user

    def _sync_department_roles(self, user):
        """Sync verified LDAP memberships into independent, scoped grants."""
        from settings_manager.models import LDAPDepartmentRoleMapping

        config = self._active_config()
        if not config:
            return

        mappings = list(
            LDAPDepartmentRoleMapping.objects.filter(ldap_config=config)
            .select_related("department")
            .prefetch_related("auth_groups")
        )

        # Retrieve the user's LDAP groups (requires AUTH_LDAP_GROUP_SEARCH)
        ldap_user = getattr(user, "ldap_user", None)
        if ldap_user is None:
            return

        try:
            user_group_dns: set = set(ldap_user.group_dns)
        except Exception:
            return

        from departments.assignment_sources import sync_external_groups

        sync_external_groups(user, "ldap", mappings, lambda mapping: mapping.ldap_group_dn in user_group_dns)
