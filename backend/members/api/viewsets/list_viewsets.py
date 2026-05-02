"""
ViewSet for MemberList and MemberListEntry management.
"""

from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from jf_manager_backend.permissions import DepartmentRoleModelPermissions
from members.api.serializers.list_serializers import (
    MemberListCreateUpdateSerializer,
    MemberListDetailSerializer,
    MemberListSerializer,
)
from members.models import Member, MemberList, MemberListEntry


@extend_schema_view(
    list=extend_schema(summary="List all member lists"),
    retrieve=extend_schema(summary="Get a member list with all entries"),
    create=extend_schema(summary="Create a new member list"),
    update=extend_schema(summary="Update a member list"),
    partial_update=extend_schema(summary="Partially update a member list"),
    destroy=extend_schema(summary="Delete a member list"),
)
class MemberListViewSet(viewsets.ModelViewSet):
    queryset = MemberList.objects.all()
    permission_classes = [IsAuthenticated, DepartmentRoleModelPermissions]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MemberListCreateUpdateSerializer
        if self.action == "retrieve":
            return MemberListDetailSerializer
        return MemberListSerializer

    # ── Membership management ──────────────────────────────────────────────

    @action(detail=True, methods=["post"])
    def add_member(self, request, pk=None):
        """POST /api/v1/member-lists/{id}/add_member/ — add a member to this list."""
        member_list = self.get_object()
        member_id = request.data.get("member_id")
        if not member_id:
            return Response({"error": "member_id erforderlich."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            member = Member.objects.get(pk=member_id)
        except Member.DoesNotExist:
            return Response({"error": "Mitglied nicht gefunden."}, status=status.HTTP_404_NOT_FOUND)

        _, created = MemberListEntry.objects.get_or_create(
            member_list=member_list,
            member=member,
        )
        return Response(
            {"added": created, "member_count": member_list.member_count},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def remove_member(self, request, pk=None):
        """POST /api/v1/member-lists/{id}/remove_member/ — remove a member from this list."""
        member_list = self.get_object()
        member_id = request.data.get("member_id")
        deleted, _ = MemberListEntry.objects.filter(member_list=member_list, member_id=member_id).delete()
        return Response({"removed": bool(deleted), "member_count": member_list.member_count})

    @action(detail=True, methods=["post"])
    def bulk_add(self, request, pk=None):
        """POST /api/v1/member-lists/{id}/bulk_add/ — add multiple members at once."""
        member_list = self.get_object()
        member_ids = request.data.get("member_ids", [])
        if not isinstance(member_ids, list):
            return Response({"error": "member_ids muss eine Liste sein."}, status=status.HTTP_400_BAD_REQUEST)

        added = 0
        for member_id in member_ids:
            try:
                member = Member.objects.get(pk=member_id)
                _, created = MemberListEntry.objects.get_or_create(member_list=member_list, member=member)
                if created:
                    added += 1
            except Member.DoesNotExist:
                pass

        return Response({"added": added, "member_count": member_list.member_count})

    # ── Check/uncheck ──────────────────────────────────────────────────────

    @action(detail=True, methods=["post"])
    def toggle_check(self, request, pk=None):
        """POST /api/v1/member-lists/{id}/toggle_check/ — toggle checked state for one member."""
        member_list = self.get_object()
        member_id = request.data.get("member_id")
        try:
            entry = MemberListEntry.objects.get(member_list=member_list, member_id=member_id)
        except MemberListEntry.DoesNotExist:
            return Response({"error": "Mitglied nicht in dieser Liste."}, status=status.HTTP_404_NOT_FOUND)
        entry.toggle_check()
        return Response({"checked": entry.checked, "checked_at": entry.checked_at})

    @action(detail=True, methods=["post"])
    def set_check(self, request, pk=None):
        """POST /api/v1/member-lists/{id}/set_check/ — set checked state for one member explicitly."""
        member_list = self.get_object()
        member_id = request.data.get("member_id")
        checked = request.data.get("checked")
        if checked is None:
            return Response({"error": "checked erforderlich."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            entry = MemberListEntry.objects.get(member_list=member_list, member_id=member_id)
        except MemberListEntry.DoesNotExist:
            return Response({"error": "Mitglied nicht in dieser Liste."}, status=status.HTTP_404_NOT_FOUND)
        entry.checked = bool(checked)
        entry.checked_at = timezone.now() if entry.checked else None
        entry.save(update_fields=["checked", "checked_at"])
        return Response({"checked": entry.checked, "checked_at": entry.checked_at})

    @action(detail=True, methods=["post"])
    def check_all(self, request, pk=None):
        """POST /api/v1/member-lists/{id}/check_all/ — mark all members as checked."""
        member_list = self.get_object()
        now = timezone.now()
        member_list.entries.update(checked=True, checked_at=now)
        return Response({"checked_count": member_list.member_count})

    @action(detail=True, methods=["post"])
    def uncheck_all(self, request, pk=None):
        """POST /api/v1/member-lists/{id}/uncheck_all/ — reset all check states."""
        member_list = self.get_object()
        member_list.entries.update(checked=False, checked_at=None)
        return Response({"checked_count": 0})

    @action(detail=True, methods=["patch"])
    def update_entry_notes(self, request, pk=None):
        """PATCH /api/v1/member-lists/{id}/update_entry_notes/ — set notes on a list entry."""
        member_list = self.get_object()
        member_id = request.data.get("member_id")
        notes = request.data.get("notes", "")
        updated = MemberListEntry.objects.filter(member_list=member_list, member_id=member_id).update(notes=notes)
        if not updated:
            return Response({"error": "Eintrag nicht gefunden."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"notes": notes})
