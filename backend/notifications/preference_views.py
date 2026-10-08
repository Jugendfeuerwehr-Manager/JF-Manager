"""Notification preferences per account and kind (NOTIF-01.5, E8): e-mail and push, never the inbox."""

from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .dispatch import kinds_for
from .models import NotificationPreference


class PreferenceSerializer(serializers.Serializer):
    kind = serializers.CharField(max_length=30)
    email = serializers.BooleanField()
    push = serializers.BooleanField()


def _rows(user):
    saved = {p.kind: p for p in NotificationPreference.objects.filter(user=user)}
    return [
        {
            "kind": kind,
            "label": label,
            "email": saved[kind].email if kind in saved else True,
            "push": saved[kind].push if kind in saved else True,
        }
        for kind, label in kinds_for(user).items()
    ]


class PreferenceView(APIView):
    """GET/PUT /notifications/preferences/ — for staff and portal accounts alike."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_rows(request.user))

    def put(self, request):
        data = PreferenceSerializer(data=request.data, many=True)
        data.is_valid(raise_exception=True)
        allowed = kinds_for(request.user)
        unknown = [row["kind"] for row in data.validated_data if row["kind"] not in allowed]
        if unknown:
            raise serializers.ValidationError({"kind": f"Unbekannte Art: {', '.join(unknown)}"})
        for row in data.validated_data:
            NotificationPreference.objects.update_or_create(
                user=request.user, kind=row["kind"], defaults={"email": row["email"], "push": row["push"]}
            )
        return Response(_rows(request.user))
