from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from .people import portal_children, portal_self
from .permissions import PortalAccountRequired


def _person(member, relation):
    # Names are always visible to the linked account (concept 4.2); further categories follow in PORTAL-02.
    return {"id": member.pk, "relation": relation, "first_name": member.name, "last_name": member.lastname}


class PortalMeView(APIView):
    """GET /api/v1/portal/me/ — the account and the people it may act for."""

    portal_access = True
    permission_classes = [PortalAccountRequired]

    @extend_schema(summary="Portal account and linked people")
    def get(self, request):
        user = request.user
        people = []
        member = portal_self(user)
        if member is not None:
            people.append(_person(member, "self"))
        people += [_person(child, "child") for child in portal_children(user)]
        return Response(
            {
                "account": {"first_name": user.first_name, "last_name": user.last_name, "email": user.email},
                "people": people,
            }
        )
