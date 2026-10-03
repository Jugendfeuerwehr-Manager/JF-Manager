from django.conf import settings
from django.db import IntegrityError, transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .models import PushDelivery, PushSubscription
from .validation import SubscriptionSerializer


class PushThrottle(UserRateThrottle):
    rate = "30/hour"
    scope = "push"


class PushConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        enabled = bool(settings.WEB_PUSH_PUBLIC_KEY and settings.WEB_PUSH_PRIVATE_KEY and settings.WEB_PUSH_SUBJECT)
        return Response({"enabled": enabled, "public_key": settings.WEB_PUSH_PUBLIC_KEY if enabled else ""})


class PushSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [PushThrottle]

    def get(self, request):
        subscription = PushSubscription.objects.filter(user=request.user, endpoint=request.query_params.get("endpoint")).first()
        return Response({"subscribed": bool(subscription), "services": subscription.services if subscription else True,
                         "orders": subscription.orders if subscription else True})

    def post(self, request):
        if not (settings.WEB_PUSH_PUBLIC_KEY and settings.WEB_PUSH_PRIVATE_KEY and settings.WEB_PUSH_SUBJECT):
            return Response({"detail": "Push ist auf diesem Server noch nicht eingerichtet."}, status=503)
        serializer = SubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            with transaction.atomic():
                subscription = PushSubscription.objects.select_for_update().filter(endpoint=data["endpoint"]).first()
                if subscription and subscription.user_id != request.user.pk:
                    return Response({"detail": "Bitte Push auf diesem Gerät neu aktivieren."}, status=409)
                if not subscription and PushSubscription.objects.filter(user=request.user).count() >= 10:
                    return Response({"detail": "Maximal zehn Geräte pro Konto."}, status=400)
                PushSubscription.objects.update_or_create(endpoint=data["endpoint"], defaults={
                    "user": request.user, "p256dh": data["keys"]["p256dh"], "auth": data["keys"]["auth"],
                    "services": data["services"], "orders": data["orders"],
                })
        except IntegrityError:
            return Response({"detail": "Bitte Push auf diesem Gerät erneut aktivieren."}, status=409)
        return Response({"subscribed": True}, status=201)

    def delete(self, request):
        PushSubscription.objects.filter(user=request.user, endpoint=request.data.get("endpoint")).delete()
        return Response(status=204)


class PushTestView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [PushThrottle]

    def post(self, request):
        subscription = PushSubscription.objects.filter(user=request.user, endpoint=request.data.get("endpoint")).first()
        if not subscription:
            return Response({"detail": "Dieses Gerät ist nicht registriert."}, status=400)
        PushDelivery.objects.create(subscription=subscription, kind="test", object_id=request.user.pk)
        return Response({"detail": "Test-Mitteilung zum Versand vorgemerkt."}, status=202)
