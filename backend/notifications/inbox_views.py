"""Inbox API (NOTIF-01.2 backend): staff inbox and portal notices."""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from portal.permissions import PortalAccountRequired, StaffAccountRequired

from .inbox import entries_for, may_see
from .models import InboxItem, InboxRecipient

PAGE = 50


def _row(entry):
    item = entry.item
    done_by = item.done_by
    return {
        "id": item.pk,
        "kind": item.kind,
        "category": item.category,
        "type": item.item_type,
        "title": item.title,
        "count": item.count,
        "link": item.link,
        "department": item.department.name if item.department_id else None,
        "department_id": item.department_id,
        "updated_at": item.updated_at,
        "created_at": item.created_at,
        "read": entry.read_at is not None,
        "task_state": item.task_state or None,
        "done_by": (done_by.get_full_name() or done_by.username) if done_by else None,
        "done_at": item.done_at,
        "done_via": item.done_via or None,
    }


def _visible(user, filters=None):
    filters = filters or {}
    entries = entries_for(user)
    if filters.get("type") in {"task", "notice"}:
        entries = entries.filter(item__item_type=filters["type"])
    if filters.get("category"):
        entries = entries.filter(item__category=filters["category"])
    if str(filters.get("department", "")).isdigit():
        entries = entries.filter(item__department_id=int(filters["department"]))
    if filters.get("unread") in {"1", "true"}:
        entries = entries.filter(read_at__isnull=True)
    if filters.get("done") not in {"1", "true"}:
        entries = entries.exclude(item__task_state=InboxItem.TaskState.DONE)
    return [e for e in entries[:500] if may_see(user, e.item)]


class InboxView(APIView):
    """GET /notifications/inbox/?type=&category=&department=&unread=&done=&offset="""

    permission_classes = [StaffAccountRequired, IsAuthenticated]

    def get(self, request):
        rows = _visible(request.user, request.query_params)
        offset = (
            int(request.query_params.get("offset", 0) or 0)
            if str(request.query_params.get("offset", "0")).isdigit()
            else 0
        )
        return Response({"count": len(rows), "results": [_row(e) for e in rows[offset : offset + PAGE]]})


class InboxCountsView(APIView):
    permission_classes = [StaffAccountRequired, IsAuthenticated]

    def get(self, request):
        rows = _visible(request.user)
        open_tasks = sum(1 for e in rows if e.item.item_type == "task" and e.item.task_state == "open")
        unread = sum(1 for e in rows if e.item.item_type == "notice" and e.read_at is None)
        return Response({"open_tasks": open_tasks, "unread_notices": unread, "total": open_tasks + unread})


def _own_entry(user, item_id):
    entry = (
        InboxRecipient.objects.select_related("item").filter(user=user, item_id=item_id, hidden_at__isnull=True).first()
    )
    if entry is None or not may_see(user, entry.item):
        raise NotFound()
    return entry


class InboxReadView(APIView):
    permission_classes = [StaffAccountRequired, IsAuthenticated]

    def post(self, request, item_id):
        entry = _own_entry(request.user, item_id)
        if entry.read_at is None:
            entry.read_at = timezone.now()
            entry.save(update_fields=["read_at"])
        return Response(_row(entry))


class BulkReadSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), min_length=1, max_length=200)


class InboxBulkReadView(APIView):
    permission_classes = [StaffAccountRequired, IsAuthenticated]

    def post(self, request):
        data = BulkReadSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        visible = {
            e.item_id for e in _visible(request.user, {"done": "1"}) if e.item_id in set(data.validated_data["ids"])
        }
        updated = InboxRecipient.objects.filter(user=request.user, item_id__in=visible, read_at__isnull=True).update(
            read_at=timezone.now()
        )
        return Response({"updated": updated})


class InboxDoneView(APIView):
    """Team status: one person marks the task done for everyone (E15)."""

    permission_classes = [StaffAccountRequired, IsAuthenticated]

    def post(self, request, item_id):
        entry = _own_entry(request.user, item_id)
        item = entry.item
        if item.item_type != InboxItem.ItemType.TASK:
            return Response({"code": "not_a_task", "detail": "Nur Aufgaben können erledigt werden."}, status=400)
        if item.task_state == InboxItem.TaskState.OPEN:
            InboxItem.objects.filter(pk=item.pk, task_state=InboxItem.TaskState.OPEN).update(
                task_state=InboxItem.TaskState.DONE, done_by=request.user, done_at=timezone.now(), done_via="ui"
            )
        entry.refresh_from_db()
        entry.item.refresh_from_db()
        return Response(_row(entry))


class PortalNotificationsView(APIView):
    """GET /portal/notifications/ — personal notices for portal accounts (no team entries)."""

    portal_access = True
    permission_classes = [PortalAccountRequired]

    def get(self, request):
        entries = entries_for(request.user).filter(item__permission="")[:100]
        return Response({"results": [_row(e) for e in entries], "unread": sum(1 for e in entries if e.read_at is None)})


class PortalNotificationReadView(APIView):
    portal_access = True
    permission_classes = [PortalAccountRequired]

    def post(self, request, item_id):
        entry = get_object_or_404(InboxRecipient, user=request.user, item_id=item_id, item__permission="")
        if entry.read_at is None:
            entry.read_at = timezone.now()
            entry.save(update_fields=["read_at"])
        return Response(_row(entry))
