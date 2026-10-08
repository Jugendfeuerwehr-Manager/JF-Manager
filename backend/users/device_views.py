"""List and end the signed-in devices of the current user."""

from django.contrib.auth import logout
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from users.devices import active_devices, end_device
from users.mfa_views import SessionUserView


def serialize(device, current_key):
    return {
        "id": device.pk,
        "user_agent": device.user_agent,
        "created_at": device.created_at.isoformat(),
        "last_seen_at": device.last_seen_at.isoformat(),
        "current": device.session_id == current_key,
    }


class DeviceListView(SessionUserView):
    """GET /api/v1/auth/devices/"""

    def get(self, request):
        current = request.session.session_key
        return Response([serialize(device, current) for device in active_devices(request.user)])


class DeviceRevokeView(SessionUserView):
    """POST /api/v1/auth/devices/<id>/revoke/ — end one session (also this one)."""

    def post(self, request, pk):
        device = get_object_or_404(active_devices(request.user), pk=pk)
        if device.session_id == request.session.session_key:
            logout(request._request)
            return Response({"revoked": 1, "current": True})
        end_device(device)
        return Response({"revoked": 1, "current": False})


class DeviceRevokeOthersView(SessionUserView):
    """POST /api/v1/auth/devices/revoke-others/ — sign out everywhere else."""

    def post(self, request):
        others = active_devices(request.user).exclude(session_id=request.session.session_key)
        count = 0
        for device in others:
            end_device(device)
            count += 1
        return Response({"revoked": count, "current": False})
