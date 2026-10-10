"""Own area of linked staff accounts: "Meine Dienste", "Meine Daten", "Meine Kinder" (PORTAL-04.3).

Mounted at ``/api/v1/my/``. These are staff endpoints: portal accounts never
reach them (no ``portal_access``, boundary middleware), and staff accounts
need a confirmed link (403 otherwise). People are resolved exactly like in the
portal (``portal_self``, ``portal_children``), and registrations use the same
participation service and rules as the portal endpoints (deadlines apply).
"""

from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from participation import portal_views

from .disclosure import parent_contact, person_payload
from .people import confirmed_link, portal_children, portal_self
from .permissions import StaffAccountRequired
from .policy import CATEGORIES, PolicySet
from .self_records import OWN_RECORD_DETAIL


class LinkedStaffAccount(BasePermission):
    """Staff account with a confirmed link to a member or parent record."""

    message = "Dein Konto ist mit keinem bestätigten Mitglieds- oder Elterndatensatz verknüpft."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and not user.is_portal_account and confirmed_link(user))


PERMISSIONS = [StaffAccountRequired, IsAuthenticated, LinkedStaffAccount]


def _may_change(user, record, permission):
    from .invitations import departments_with_permission, record_department_ids

    allowed = departments_with_permission(user, permission)
    return allowed is None or bool(allowed & record_department_ids(record))


class OwnOverviewView(APIView):
    """GET /api/v1/my/ — own member record, children of the own parent record and edit rights."""

    permission_classes = PERMISSIONS

    def get(self, request):
        user = request.user
        link = confirmed_link(user)
        policies = PolicySet.load()
        people = []
        member = portal_self(user)
        if member is not None:
            people.append(portal_views_person(member, "self", policies))
        children = list(portal_children(user).prefetch_related("departments"))
        people += [portal_views_person(child, "child", policies) for child in children]
        return Response(
            {
                "account": {"first_name": user.first_name, "last_name": user.last_name, "email": user.email},
                "people": people,
                "parent": parent_contact(link.parent) if link.parent_id else None,
                "link": {"id": link.pk, "member_id": link.member_id, "parent_id": link.parent_id},
                "can_edit": {
                    "member": bool(member) and _may_change(user, member, "members.change_member"),
                    "parent": bool(link.parent_id) and _may_change(user, link.parent, "members.change_parent"),
                },
                "evidence_notice": OWN_RECORD_DETAIL,
            }
        )


def portal_views_person(member, relation, policies):
    from .views import _person

    return _person(member, relation, policies)


class OwnPersonView(APIView):
    """GET /api/v1/my/people/<id>/ — own data in full portal categories; children as their parent sees them."""

    permission_classes = PERMISSIONS

    def get(self, request, member_id):
        user = request.user
        own = portal_self(user)
        if own is not None and own.pk == member_id:
            # The account's own record: every category (it is the person's own data, E14).
            data = person_payload(own, "self", policies=_all_visible())
            # Qualifications kept at the account itself also count (E10); shown read-only.
            data["account_qualifications"] = _account_qualifications(user)
            return Response(data)
        child = portal_children(user).filter(pk=member_id).first()
        if child is None:
            raise NotFound()
        return Response(person_payload(child, "child", viewer_parent=confirmed_link(user).parent))


class _AllVisible(PolicySet):
    """Policy view for the own record: all categories visible."""

    def __init__(self):
        pass

    def visible_categories(self, audience, department_ids):
        return [key for key in CATEGORIES if key != "other_parents"]

    def department_value(self, department_id, key, audience):
        return "visible"


def _account_qualifications(user):
    from django.utils import timezone

    today = timezone.localdate()
    rows = user.qualifications.select_related("type").order_by("type__name")
    return [
        {
            "type": q.type.name,
            "acquired": q.date_acquired.isoformat() if q.date_acquired else None,
            "expires": q.date_expires.isoformat() if q.date_expires else None,
            "valid": q.date_expires is None or q.date_expires >= today,
        }
        for q in rows
    ]


def _all_visible():
    return _AllVisible()


class _OwnMixin:
    portal_access = False
    permission_classes = PERMISSIONS


class OwnSessionListView(_OwnMixin, portal_views.SessionListView):
    """GET /api/v1/my/sessions/?person= — same list as the portal."""


class OwnSessionRegistrationView(_OwnMixin, portal_views.SessionRegistrationView):
    """PUT /api/v1/my/sessions/<sid>/registrations/<mid>/ — register or cancel oneself or an own child."""


class OwnAbsencePreviewView(_OwnMixin, portal_views.AbsencePreviewView):
    pass


class OwnAbsenceView(_OwnMixin, portal_views.AbsenceView):
    pass
