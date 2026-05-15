"""
ViewSet for OIDC Group Mappings.

Mirrors LDAPDepartmentMappingViewSet — provides list/create/destroy
for OIDCGroupMapping records (OIDC group claim value → department role).
"""

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from settings_manager.models import OIDCConfig, OIDCGroupMapping

from ..serializers import OIDCGroupMappingSerializer


class OIDCGroupMappingViewSet(viewsets.ViewSet):
    """
    ViewSet for managing OIDC Group → Department role mappings.

    Endpoints:
        GET  /api/v1/oidc-group-mappings/   — list all mappings
        POST /api/v1/oidc-group-mappings/   — create a mapping
        DELETE /api/v1/oidc-group-mappings/{id}/ — delete a mapping
    """

    permission_classes = [IsAuthenticated]

    def _check_permission(self, user):
        if user.is_superuser:
            return True
        return user.has_perm("settings_manager.change_oidc_settings") or user.has_perm(
            "settings_manager.change_all_settings"
        )

    def list(self, request):
        if not self._check_permission(request.user):
            return Response(
                {"detail": "Keine Berechtigung für OIDC-Einstellungen."},
                status=status.HTTP_403_FORBIDDEN,
            )

        config = OIDCConfig.get_or_create_default()
        mappings = (
            OIDCGroupMapping.objects.filter(oidc_config=config)
            .select_related("department")
            .prefetch_related("auth_groups")
        )
        serializer = OIDCGroupMappingSerializer(mappings, many=True)
        return Response(serializer.data)

    def create(self, request):
        if not self._check_permission(request.user):
            return Response(
                {"detail": "Keine Berechtigung für OIDC-Einstellungen."},
                status=status.HTTP_403_FORBIDDEN,
            )

        config = OIDCConfig.get_or_create_default()
        serializer = OIDCGroupMappingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(oidc_config=config)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        if not self._check_permission(request.user):
            return Response(
                {"detail": "Keine Berechtigung für OIDC-Einstellungen."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            config = OIDCConfig.get_or_create_default()
            mapping = OIDCGroupMapping.objects.get(pk=pk, oidc_config=config)
        except OIDCGroupMapping.DoesNotExist:
            return Response(
                {"detail": "Mapping nicht gefunden."},
                status=status.HTTP_404_NOT_FOUND,
            )

        mapping.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
