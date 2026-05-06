from django.conf import settings
from django_auth_ldap.backend import LDAPBackend
from django_auth_ldap.config import ActiveDirectoryGroupType, GroupOfNamesType, LDAPSearch

from settings_manager.models import LDAPConfig


def _set_setting(name, value):
    setattr(settings, name, value)


class ConfigurableLDAPBackend(LDAPBackend):
    """
    LDAP backend that reads runtime configuration from LDAPConfig.
    Returns None when LDAP is disabled/misconfigured so Django can fall back to
    ModelBackend for local accounts.
    """

    def _active_config(self):
        return LDAPConfig.objects.order_by("id").first()

    def _configure_runtime(self):
        config = self._active_config()
        if not config or not config.enabled:
            return False

        if not config.server_uri or not config.user_search_base_dn or not config.user_search_filter:
            return False

        try:
            import ldap
        except Exception:
            return False

        _set_setting("AUTH_LDAP_SERVER_URI", config.server_uri)
        _set_setting("AUTH_LDAP_START_TLS", config.start_tls)
        _set_setting("AUTH_LDAP_BIND_DN", config.bind_dn)
        _set_setting("AUTH_LDAP_BIND_PASSWORD", config.bind_password or "")
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

            _set_setting("AUTH_LDAP_MIRROR_GROUPS", config.mirror_groups)
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
        return user

    def _sync_department_roles(self, user):
        """
        After a successful LDAP login, sync UserDepartmentRole records based on
        the LDAPDepartmentRoleMapping configuration.

        For every mapping where the user is a member of the LDAP group:
        - Ensure a UserDepartmentRole exists for user+department
        - Merge the mapped auth groups into the role

        If ``revoke_on_mismatch=True`` is set on a mapping and the user is NOT
        in the LDAP group, the corresponding UserDepartmentRole is removed.
        """
        from departments.models import UserDepartmentRole
        from settings_manager.models import LDAPDepartmentRoleMapping

        config = self._active_config()
        if not config:
            return

        mappings = list(
            LDAPDepartmentRoleMapping.objects.filter(ldap_config=config)
            .select_related("department")
            .prefetch_related("auth_groups")
        )
        if not mappings:
            return

        # Retrieve the user's LDAP groups (requires AUTH_LDAP_GROUP_SEARCH)
        ldap_user = getattr(user, "ldap_user", None)
        if ldap_user is None:
            return

        try:
            user_group_dns: set = set(ldap_user.group_dns)
        except Exception:
            return

        for mapping in mappings:
            is_member = mapping.ldap_group_dn in user_group_dns

            if is_member:
                role, _ = UserDepartmentRole.objects.get_or_create(
                    user=user,
                    department=mapping.department,
                )
                existing_ids = set(role.groups.values_list("id", flat=True))
                mapped_ids = set(mapping.auth_groups.values_list("id", flat=True))
                role.groups.set(list(existing_ids | mapped_ids))
            elif mapping.revoke_on_mismatch:
                UserDepartmentRole.objects.filter(
                    user=user,
                    department=mapping.department,
                ).delete()
