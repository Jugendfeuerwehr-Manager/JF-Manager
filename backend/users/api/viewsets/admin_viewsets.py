from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import extend_schema

from users.api.permissions import IsAdminUser
from users.api.serializers.admin_serializers import (
    AdminUserListSerializer,
    AdminUserDetailSerializer,
    AdminUserWriteSerializer,
    AuthGroupListSerializer,
    AuthGroupDetailSerializer,
    AuthGroupWriteSerializer,
    PermissionSerializer,
)

User = get_user_model()


PERMISSION_DESCRIPTIONS = {
    # Members
    'view_member': 'Mitglieder ansehen – Zugriff auf die Mitgliederliste und Detailansichten.',
    'add_member': 'Mitglieder anlegen – Neue Mitglieder im System erfassen.',
    'change_member': 'Mitglieder bearbeiten – Bestehende Mitgliederdaten ändern.',
    'delete_member': 'Mitglieder löschen – Mitglieder aus dem System entfernen.',
    # Parents
    'view_parent': 'Eltern ansehen – Zugriff auf Elternkontakte.',
    'add_parent': 'Eltern anlegen – Neue Elternkontakte erstellen.',
    'change_parent': 'Eltern bearbeiten – Elterndaten aktualisieren.',
    'delete_parent': 'Eltern löschen – Elternkontakte entfernen.',
    # Events / Log
    'view_event': 'Protokoll ansehen – Einträge im Protokoll lesen.',
    'add_event': 'Protokoll-Eintrag erstellen – Neue Einträge im Protokoll anlegen.',
    'change_event': 'Protokoll bearbeiten – Bestehende Einträge ändern.',
    'delete_event': 'Protokoll löschen – Einträge aus dem Protokoll entfernen.',
    # Event Types
    'view_eventtype': 'Eintragstypen ansehen – Verfügbare Eintragstypen einsehen.',
    'add_eventtype': 'Eintragstypen anlegen – Neue Eintragstypen erstellen.',
    'change_eventtype': 'Eintragstypen bearbeiten – Bestehende Eintragstypen ändern.',
    'delete_eventtype': 'Eintragstypen löschen – Eintragstypen entfernen.',
    # Orders
    'view_order': 'Bestellungen ansehen – Zugriff auf alle Bestellungen.',
    'add_order': 'Bestellungen erstellen – Neue Bestellungen aufgeben.',
    'change_order': 'Bestellungen bearbeiten – Bestellstatus und Details ändern.',
    'delete_order': 'Bestellungen löschen – Bestellungen entfernen.',
    # Order Items
    'view_orderitem': 'Bestellpositionen ansehen – Einzelne Positionen einer Bestellung sehen.',
    'add_orderitem': 'Bestellpositionen hinzufügen – Artikel zu Bestellungen hinzufügen.',
    'change_orderitem': 'Bestellpositionen bearbeiten – Bestellpositionen ändern.',
    'delete_orderitem': 'Bestellpositionen löschen – Positionen aus Bestellungen entfernen.',
    # Orderable Items
    'view_orderableitem': 'Bestellbare Artikel ansehen – Katalog der bestellbaren Artikel.',
    'add_orderableitem': 'Bestellbare Artikel anlegen – Neue Artikel zum Katalog hinzufügen.',
    'change_orderableitem': 'Bestellbare Artikel bearbeiten – Katalogeinträge ändern.',
    'delete_orderableitem': 'Bestellbare Artikel löschen – Artikel aus dem Katalog entfernen.',
    # Order Statuses
    'view_orderstatus': 'Bestellstatus ansehen – Verfügbare Status einsehen.',
    'add_orderstatus': 'Bestellstatus anlegen – Neue Status erstellen.',
    'change_orderstatus': 'Bestellstatus bearbeiten – Bestehende Status ändern.',
    'delete_orderstatus': 'Bestellstatus löschen – Status entfernen.',
    # Inventory
    'view_item': 'Inventar-Artikel ansehen – Artikel im Inventar einsehen.',
    'add_item': 'Inventar-Artikel anlegen – Neue Artikel erfassen.',
    'change_item': 'Inventar-Artikel bearbeiten – Artikeldaten ändern.',
    'delete_item': 'Inventar-Artikel löschen – Artikel aus dem Inventar entfernen.',
    'view_stock': 'Bestand ansehen – Lagerbestände einsehen.',
    'add_stock': 'Bestand anlegen – Neue Bestandseinträge erstellen.',
    'change_stock': 'Bestand bearbeiten – Bestandsdaten ändern.',
    'delete_stock': 'Bestand löschen – Bestandseinträge entfernen.',
    'view_transaction': 'Transaktionen ansehen – Lagerbewegungen einsehen.',
    'add_transaction': 'Transaktionen anlegen – Neue Lagerbewegungen erfassen.',
    'view_storagelocation': 'Lagerorte ansehen – Verfügbare Lagerorte einsehen.',
    'add_storagelocation': 'Lagerorte anlegen – Neue Lagerorte erstellen.',
    'change_storagelocation': 'Lagerorte bearbeiten – Lagerorte ändern.',
    'delete_storagelocation': 'Lagerorte löschen – Lagerorte entfernen.',
    'view_category': 'Kategorien ansehen – Artikelkategorien einsehen.',
    'add_category': 'Kategorien anlegen – Neue Kategorien erstellen.',
    'change_category': 'Kategorien bearbeiten – Kategorien ändern.',
    'delete_category': 'Kategorien löschen – Kategorien entfernen.',
    # Servicebook
    'view_service': 'Dienste ansehen – Dienstbuch-Einträge einsehen.',
    'add_service': 'Dienste anlegen – Neue Dienste erstellen.',
    'change_service': 'Dienste bearbeiten – Diensteinträge ändern.',
    'delete_service': 'Dienste löschen – Diensteinträge entfernen.',
    'view_attendance': 'Anwesenheiten ansehen – Teilnahmen einsehen.',
    'add_attendance': 'Anwesenheiten anlegen – Teilnahmen erfassen.',
    'change_attendance': 'Anwesenheiten bearbeiten – Teilnahmen ändern.',
    'delete_attendance': 'Anwesenheiten löschen – Teilnahmen entfernen.',
    # Qualifications
    'view_qualification': 'Qualifikationen ansehen – Qualifikationen einsehen.',
    'add_qualification': 'Qualifikationen anlegen – Neue Qualifikationen erstellen.',
    'change_qualification': 'Qualifikationen bearbeiten – Qualifikationen ändern.',
    'delete_qualification': 'Qualifikationen löschen – Qualifikationen entfernen.',
    'view_qualificationtype': 'Qualifikationstypen ansehen – Typen einsehen.',
    'add_qualificationtype': 'Qualifikationstypen anlegen – Neue Typen erstellen.',
    'change_qualificationtype': 'Qualifikationstypen bearbeiten – Typen ändern.',
    'delete_qualificationtype': 'Qualifikationstypen löschen – Typen entfernen.',
    # Special Tasks
    'view_specialtask': 'Sonderaufgaben ansehen – Sonderaufgaben einsehen.',
    'add_specialtask': 'Sonderaufgaben anlegen – Neue Sonderaufgaben erstellen.',
    'change_specialtask': 'Sonderaufgaben bearbeiten – Sonderaufgaben ändern.',
    'delete_specialtask': 'Sonderaufgaben löschen – Sonderaufgaben entfernen.',
    # Users
    'view_customuser': 'Benutzer ansehen – Benutzerliste und Details einsehen.',
    'add_customuser': 'Benutzer anlegen – Neue Benutzer erstellen.',
    'change_customuser': 'Benutzer bearbeiten – Benutzerdaten ändern.',
    'delete_customuser': 'Benutzer löschen – Benutzer entfernen.',
    # Groups
    'view_group': 'Gruppen ansehen – Berechtigungsgruppen einsehen.',
    'add_group': 'Gruppen anlegen – Neue Berechtigungsgruppen erstellen.',
    'change_group': 'Gruppen bearbeiten – Gruppenzuweisungen und Berechtigungen ändern.',
    'delete_group': 'Gruppen löschen – Berechtigungsgruppen entfernen.',
    # Settings
    'view_all_settings': 'Alle Einstellungen ansehen – Zugriff auf sämtliche Einstellungen.',
    'change_all_settings': 'Alle Einstellungen bearbeiten – Sämtliche Einstellungen ändern.',
    # Email
    'can_send_member_emails': 'E-Mails senden – E-Mails an Mitglieder versenden.',
    # Attachments
    'view_attachment': 'Anhänge ansehen – Dateianhänge einsehen.',
    'add_attachment': 'Anhänge hochladen – Neue Dateien hochladen.',
    'change_attachment': 'Anhänge bearbeiten – Anhänge ändern.',
    'delete_attachment': 'Anhänge löschen – Anhänge entfernen.',
}

# Relevant app labels to filter permissions
RELEVANT_APP_LABELS = [
    'members', 'orders', 'inventory', 'servicebook',
    'qualifications', 'users', 'auth', 'settings_manager',
]


class AdminUserViewSet(viewsets.ModelViewSet):
    """Admin-only viewset for managing users, groups, and permissions."""
    queryset = User.objects.prefetch_related('groups', 'user_permissions').order_by('username')
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'email', 'date_joined', 'last_login', 'is_active']
    ordering = ['username']
    filterset_fields = ['is_active', 'is_staff', 'is_superuser']

    def get_serializer_class(self):
        if self.action == 'list':
            return AdminUserListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return AdminUserWriteSerializer
        return AdminUserDetailSerializer

    def perform_destroy(self, instance):
        if instance == self.request.user:
            from rest_framework.exceptions import ValidationError
            raise ValidationError('Sie können Ihren eigenen Account nicht löschen.')
        instance.is_active = False
        instance.save()

    @extend_schema(summary="Set user groups")
    @action(detail=True, methods=['patch'], url_path='set-groups')
    def set_groups(self, request, pk=None):
        user = self.get_object()
        group_ids = request.data.get('group_ids', [])
        try:
            groups = Group.objects.filter(id__in=group_ids)
            user.groups.set(groups)
            return Response(AdminUserDetailSerializer(user).data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AuthGroupViewSet(viewsets.ModelViewSet):
    """Admin-only viewset for managing Django auth groups and their permissions."""
    queryset = Group.objects.prefetch_related('permissions', 'user_set').order_by('name')
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'list':
            return AuthGroupListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return AuthGroupWriteSerializer
        return AuthGroupDetailSerializer


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset listing available Django permissions with descriptions."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = PermissionSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'codename']
    ordering = ['content_type__app_label', 'codename']

    def get_queryset(self):
        return Permission.objects.select_related('content_type').filter(
            content_type__app_label__in=RELEVANT_APP_LABELS
        )

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # Enrich with descriptions
        for perm in response.data.get('results', response.data):
            codename = perm.get('codename', '')
            perm['description'] = PERMISSION_DESCRIPTIONS.get(codename, '')
        return response
