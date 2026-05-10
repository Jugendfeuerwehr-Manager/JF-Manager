"""
ViewSet for LDAP → Department Role Mappings
"""

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from settings_manager.models import LDAPConfig, LDAPDepartmentRoleMapping

from ..serializers import LDAPDepartmentRoleMappingSerializer


class LDAPDepartmentMappingViewSet(viewsets.ViewSet):
    """
    CRUD API for LDAP → Department role mappings.

    list:   GET  /api/v1/ldap-department-mappings/
    create: POST /api/v1/ldap-department-mappings/
    delete: DELETE /api/v1/ldap-department-mappings/{id}/
    """

    permission_classes = [IsAuthenticated]

    def _check_perm(self, user):
        if user.is_superuser:
            return True
        return user.has_perm("settings_manager.change_ldap_settings") or user.has_perm(
            "settings_manager.change_all_settings"
        )

    def _check_view_perm(self, user):
        if user.is_superuser:
            return True
        return (
            user.has_perm("settings_manager.view_ldap_settings")
            or user.has_perm("settings_manager.change_ldap_settings")
            or user.has_perm("settings_manager.view_all_settings")
            or user.has_perm("settings_manager.change_all_settings")
        )

    def list(self, request):
        if not self._check_view_perm(request.user):
            return Response({"detail": "Keine Berechtigung."}, status=status.HTTP_403_FORBIDDEN)
        config = LDAPConfig.get_or_create_default()
        qs = (
            LDAPDepartmentRoleMapping.objects.filter(ldap_config=config)
            .select_related("department")
            .prefetch_related("auth_groups")
        )
        serializer = LDAPDepartmentRoleMappingSerializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request):
        if not self._check_perm(request.user):
            return Response({"detail": "Keine Berechtigung."}, status=status.HTTP_403_FORBIDDEN)
        config = LDAPConfig.get_or_create_default()
        serializer = LDAPDepartmentRoleMappingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(ldap_config=config)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        if not self._check_perm(request.user):
            return Response({"detail": "Keine Berechtigung."}, status=status.HTTP_403_FORBIDDEN)
        config = LDAPConfig.get_or_create_default()
        try:
            mapping = LDAPDepartmentRoleMapping.objects.get(pk=pk, ldap_config=config)
        except LDAPDepartmentRoleMapping.DoesNotExist:
            return Response({"detail": "Nicht gefunden."}, status=status.HTTP_404_NOT_FOUND)
        mapping.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
