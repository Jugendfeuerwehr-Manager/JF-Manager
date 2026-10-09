"""Resolve and execute quick-action links (NOTIF-01.4). POST only; GET never changes anything."""

from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import actions

MESSAGES = {
    "invalid": "Dieser Link ist ungültig.",
    "expired": "Dieser Link ist abgelaufen.",
    "wrong_account": "Dieser Link gehört zu einem anderen Konto.",
    "gone": "Diese Aktion ist nicht mehr verfügbar.",
}


class TokenInput(serializers.Serializer):
    token = serializers.CharField(max_length=actions.MAX_TOKEN_LENGTH)
    payload = serializers.DictField(required=False, default=dict)


def _error(user, code, status):
    # The target stays generic: no hint whether the object exists (4.9.4).
    return Response(
        {"code": code, "detail": MESSAGES[code], "target_route": actions.generic_route(user)}, status=status
    )


class ActionView(APIView):
    """Reachable for staff and portal accounts (allowlisted view names); each action checks its own rights."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["post", "options"]
    handler = None

    def post(self, request):
        data = TokenInput(data=request.data)
        if not data.is_valid():
            return _error(request.user, "invalid", 400)
        try:
            return Response(type(self).handler(request.user, data.validated_data))
        except actions.InvalidToken:
            return _error(request.user, "invalid", 400)
        except actions.WrongAccount:
            return _error(request.user, "wrong_account", 403)
        except actions.Expired:
            return _error(request.user, "expired", 410)
        except actions.Gone:
            return _error(request.user, "gone", 404)


def _resolve(user, data):
    return actions.resolve(user, data["token"])


def _execute(user, data):
    return actions.execute(user, data["token"], data.get("payload"))


class ResolveView(ActionView):
    handler = staticmethod(_resolve)


class ExecuteView(ActionView):
    handler = staticmethod(_execute)
