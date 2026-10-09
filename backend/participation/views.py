"""Staff endpoints for eligibility rules (PART-03.3)."""

from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from portal.permissions import StaffAccountRequired
from training.api.permissions import can_manage_training_department
from training.models import TrainingSession

from .eligibility import evaluate_members, neutral_audience_notice
from .rules import Names, summarize, validate_rule

MAX_TARGET = 500


def may_plan_anywhere(user):
    """Training planner in at least one department (or organisation-wide)."""
    if user.is_superuser or user.has_perm("training.can_manage_training"):
        return True
    return user.department_roles.filter(
        groups__permissions__content_type__app_label="training",
        groups__permissions__codename="can_manage_training",
    ).exists()


def target_members(session):
    """Target group of a session.

    Members of the session's groups; without groups all members of its department. Member has no
    "active" flag in the data model (membership state is the free-form ``status``, which a rule can
    filter on), so every member record counts. Returns ``None`` for a session without groups and department.
    """
    from members.models import Member

    group_ids = list(session.groups.values_list("pk", flat=True))
    if group_ids:
        queryset = Member.objects.filter(group_id__in=group_ids)
    elif session.department_id:
        queryset = Member.objects.filter(departments=session.department_id)
    else:
        return None
    return queryset.order_by("lastname", "name", "pk").only("pk", "name", "lastname")[: MAX_TARGET + 1]


class RuleView(APIView):
    permission_classes = [StaffAccountRequired, IsAuthenticated]

    def parse_rule(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        return data.get("rule")


class EligibilityValidateView(RuleView):
    def post(self, request):
        if not may_plan_anywhere(request.user):
            raise PermissionDenied("Keine Berechtigung zur Dienstplanung.")
        rule = self.parse_rule(request)
        errors = validate_rule(rule)
        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "summary": summarize(rule, Names.for_rule(rule)),
                "errors": {},
                "audience_notice": neutral_audience_notice(rule),
            }
        )


class EligibilityPreviewView(RuleView):
    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        session_id = data.get("session")
        if isinstance(session_id, bool) or not isinstance(session_id, int):
            return Response({"errors": {"session": "Dienst ist erforderlich"}}, status=status.HTTP_400_BAD_REQUEST)
        session = TrainingSession.objects.filter(pk=session_id).first()
        if session is None:
            raise NotFound("Dienst nicht gefunden.")
        if not can_manage_training_department(request.user, session.department_id):
            raise PermissionDenied("Keine Berechtigung für diesen Dienst.")
        rule = data.get("rule")
        errors = validate_rule(rule)
        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        members = target_members(session)
        if members is None:
            return Response(
                {"errors": {"session": "Der Dienst hat weder Gruppen noch eine Abteilung als Zielgruppe"}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        members = list(members)
        if len(members) > MAX_TARGET:
            return Response(
                {"errors": {"session": f"Die Zielgruppe ist größer als {MAX_TARGET} Personen"}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        results = evaluate_members(rule, [m.pk for m in members], session.date)
        excluded = [
            {"member_id": m.pk, "name": f"{m.name} {m.lastname}".strip(), "reasons": results[m.pk].reasons}
            for m in members
            if not results[m.pk].ok
        ]
        return Response(
            {
                "summary": summarize(rule, Names.for_rule(rule)),
                "total": len(members),
                "eligible": len(members) - len(excluded),
                "excluded": excluded,
                "errors": {},
                "audience_notice": neutral_audience_notice(rule),
            }
        )
