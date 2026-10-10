"""
API viewsets for email messaging system.
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from departments.mixins import DepartmentScopeViewSetMixin
from members.api.permissions import CanSendEmails, sending_department_ids
from members.api.serializers.email_serializers import (
    EmailMessageCreateSerializer,
    EmailMessageDetailSerializer,
    EmailMessageListSerializer,
    EmailPreviewRequestSerializer,
    EmailPreviewResponseSerializer,
    EmailTemplateVariablesSerializer,
)
from members.models import EmailAttachment, EmailMessage, Member
from members.services.email_service import (
    EmailRecipientCollector,
    EmailTemplateRenderer,
    MemberEmailService,
    uses_personalization,
)


class EmailMessageViewSet(DepartmentScopeViewSetMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing email messages.

    Provides endpoints for creating, listing, and sending emails to members.
    """

    queryset = EmailMessage.objects.all()
    permission_classes = [IsAuthenticated, CanSendEmails]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["subject", "recipient_member__name", "recipient_member__lastname"]
    filterset_fields = ["status", "recipient_type", "recipient_group", "sender"]
    ordering_fields = ["created_at", "sent_at", "subject"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "list":
            return EmailMessageListSerializer
        elif self.action == "create":
            return EmailMessageCreateSerializer
        return EmailMessageDetailSerializer

    def get_queryset(self):
        """Filter queryset based on user permissions."""
        queryset = super().get_queryset()

        if not self.request.user.is_superuser:
            queryset = queryset.filter(sender=self.request.user)
        if not self.request.user.has_perm("members.can_send_member_emails"):
            queryset = queryset.filter(department_id__in=sending_department_ids(self.request.user))

        return queryset

    def _get_accessible_member_queryset(self):
        """
        Return a Member queryset filtered to the departments accessible
        to the current user, mirroring MemberViewSet.get_queryset() logic.
        """
        base_qs = Member.objects.prefetch_related("departments")
        allowed_ids = self._sending_department_ids()
        if allowed_ids is None:
            return base_qs
        return base_qs.filter(departments__id__in=allowed_ids).distinct()

    def _sending_department_ids(self):
        """Departments the caller may send to; ``None`` means every department."""
        user = self.request.user
        has_global_right = user.has_perm("members.can_send_member_emails")
        requested_dept = self._resolve_requested_department(user)
        if self._user_is_org_wide(user) and has_global_right:
            return None if requested_dept is None else [requested_dept]
        allowed_ids = list(self._user_department_ids(user) if has_global_right else sending_department_ids(user))
        if requested_dept is not None:
            allowed_ids = [requested_dept] if requested_dept in allowed_ids else []
        return allowed_ids

    def _validate_targets(self, data, member_qs):
        """Reject recipients and a department label outside the sending scope
        before anything is stored or sent."""
        errors = {}
        member = data.get("recipient_member")
        if member is not None and not member_qs.filter(pk=member.pk).exists():
            errors["recipient_member"] = "Mitglied nicht gefunden oder kein Versandrecht."
        members = data.get("recipient_members") or []
        if members and member_qs.filter(pk__in=[m.pk for m in members]).count() != len({m.pk for m in members}):
            errors["recipient_members"] = "Mindestens ein Mitglied liegt außerhalb Ihres Versandbereichs."
        allowed_ids = self._sending_department_ids()
        department = data.get("department")
        if department is not None and allowed_ids is not None and department.pk not in allowed_ids:
            errors["department"] = "Kein Versandrecht für diese Abteilung."
        group = data.get("recipient_group")
        if (
            group is not None
            and group.department_id is not None
            and allowed_ids is not None
            and group.department_id not in allowed_ids
        ):
            errors["recipient_group"] = "Kein Versandrecht für die Abteilung dieser Gruppe."
        if errors:
            raise ValidationError(errors)

    def perform_create(self, serializer):
        self._validate_targets(serializer.validated_data, self._get_accessible_member_queryset())
        serializer.save()

    def perform_update(self, serializer):
        self._validate_targets(serializer.validated_data, self._get_accessible_member_queryset())
        serializer.save()

    @action(detail=False, methods=["post"])
    def send(self, request):
        """
        Create and send an email message with optional file attachments.

        POST /api/v1/emails/send/

        Accepts multipart/form-data with:
        - subject, body_html, body_text, recipient_type, recipient_group, recipient_member
        - attachments: one or more files (field name: "attachments")
        """
        create_serializer = EmailMessageCreateSerializer(data=request.data, context={"request": request})
        create_serializer.is_valid(raise_exception=True)
        self._validate_targets(create_serializer.validated_data, self._get_accessible_member_queryset())

        from jf_manager_backend.upload_safety import validate_batch

        files = request.FILES.getlist("attachments")
        try:
            content_types = validate_batch(files)
        except ValidationError as exc:
            return Response({"error": str(exc.detail["file"])}, status=status.HTTP_400_BAD_REQUEST)
        # Validate the entire batch before creating the message or storing any file.
        email_message = create_serializer.save()
        for f, content_type in zip(files, content_types, strict=True):
            EmailAttachment.objects.create(
                email_message=email_message,
                file=f,
                original_filename=f.name,
                file_size=f.size,
                content_type=content_type,
            )

        try:
            # Prepare recipients (department-scoped)
            member_qs = self._get_accessible_member_queryset()
            recipient_count = MemberEmailService.prepare_recipients(email_message, member_qs=member_qs)

            if recipient_count == 0:
                return Response({"error": "Keine Empfänger gefunden"}, status=status.HTTP_400_BAD_REQUEST)

            # Send emails
            result = MemberEmailService.send_email_message(email_message)

            # Return detailed response
            detail_serializer = EmailMessageDetailSerializer(email_message)

            return Response({"email": detail_serializer.data, "result": result}, status=status.HTTP_201_CREATED)

        except Exception as e:
            email_message.status = "failed"
            email_message.error_message = str(e)
            email_message.save()

            return Response(
                {"error": "Beim Versenden der E-Mail ist ein interner Fehler aufgetreten."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def resend(self, request, pk=None):
        """
        Resend failed recipients for an email message.

        POST /api/v1/emails/{id}/resend/
        """
        email_message = self.get_object()

        # Reset failed recipients to pending
        failed_recipients = email_message.recipients.filter(status="failed")
        failed_recipients.update(status="pending", error_message="")

        # Send again
        result = MemberEmailService.send_email_message(email_message)

        detail_serializer = EmailMessageDetailSerializer(email_message)

        return Response({"email": detail_serializer.data, "result": result})

    @action(detail=False, methods=["post"])
    def preview(self, request):
        """
        Preview an email with template rendering for a specific member.

        POST /api/v1/emails/preview/

        Request body:
        {
            "subject": "Email subject",
            "body_html": "<p>Hello {{vorname}}</p>",
            "body_text": "Hello {{vorname}}",
            "member_id": 1
        }
        """
        request_serializer = EmailPreviewRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        # Validate the requested member is accessible to the current user
        member_qs = self._get_accessible_member_queryset()
        member = member_qs.filter(id=request_serializer.validated_data["member_id"]).first()
        if not member:
            return Response({"error": "Mitglied nicht gefunden oder kein Zugriff"}, status=status.HTTP_404_NOT_FOUND)

        # Render template (signature is already included in body_html by the frontend)
        layout = request_serializer.validated_data.get("layout") or "none"
        rendered_html, rendered_text = EmailTemplateRenderer.render_for_member(
            request_serializer.validated_data["body_html"],
            request_serializer.validated_data.get("body_text", ""),
            member,
            layout=layout,
        )

        # Get recipient count for this member
        recipients = EmailRecipientCollector.get_member_emails(member)

        response_data = {
            "rendered_html": rendered_html,
            "rendered_text": rendered_text,
            "member_name": member.get_full_name(),
            "recipient_count": len(recipients),
        }

        response_serializer = EmailPreviewResponseSerializer(response_data)
        return Response(response_serializer.data)

    @action(detail=False, methods=["get"])
    def template_variables(self, request):
        """
        Get list of available template variables.

        GET /api/v1/emails/template_variables/
        """
        variables = EmailTemplateRenderer.get_available_variables()
        serializer = EmailTemplateVariablesSerializer(variables, many=True)
        return Response(serializer.data)

    def _selected_members(self, data):
        """Members targeted by a recipient selection inside the sending scope.

        Returns ``(members, error_response)``; unknown or foreign targets give the same
        404 so the check does not reveal records outside the caller's scope.
        """
        from members.models import Group

        recipient_type = data.get("recipient_type")
        member_qs = self._get_accessible_member_queryset()
        if recipient_type == "all":
            return EmailRecipientCollector.members_for("all", member_qs=member_qs), None
        if recipient_type == "group":
            group_id = data.get("recipient_group")
            if not group_id:
                return None, Response({"error": "recipient_group erforderlich"}, status=status.HTTP_400_BAD_REQUEST)
            group = Group.objects.filter(pk=group_id).first() if str(group_id).isdigit() else None
            allowed_ids = self._sending_department_ids()
            if group is None or (
                group.department_id is not None and allowed_ids is not None and group.department_id not in allowed_ids
            ):
                return None, Response(
                    {"error": "Gruppe nicht gefunden oder kein Zugriff"}, status=status.HTTP_404_NOT_FOUND
                )
            return EmailRecipientCollector.members_for("group", group=group, member_qs=member_qs), None
        if recipient_type == "individual":
            member_id = data.get("recipient_member")
            if not member_id:
                return None, Response({"error": "recipient_member erforderlich"}, status=status.HTTP_400_BAD_REQUEST)
            member = member_qs.filter(id=member_id).first() if str(member_id).isdigit() else None
            if not member:
                return None, Response(
                    {"error": "Mitglied nicht gefunden oder kein Zugriff"}, status=status.HTTP_404_NOT_FOUND
                )
            return EmailRecipientCollector.members_for("individual", member=member, member_qs=member_qs), None
        if recipient_type == "multiple":
            member_ids = data.get("recipient_members") or []
            if not isinstance(member_ids, list) or not member_ids:
                return None, Response({"error": "recipient_members erforderlich"}, status=status.HTTP_400_BAD_REQUEST)
            member_ids = [int(item) for item in member_ids if str(item).isdigit()]
            return EmailRecipientCollector.members_for("multiple", members=member_ids, member_qs=member_qs), None
        return None, Response({"error": "Ungültiger recipient_type"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def recipient_check(self, request):
        """
        Recipient check before sending (UX-07.1).

        POST /api/v1/emails/recipient_check/

        Same selection as ``recipient_count`` plus optional ``body_html``/``body_text``.
        Returns the deliveries that would be created (count and list), the members and
        addresses that are excluded with a reason, and how many duplicate addresses were
        merged. Personalised messages (member variables) are never merged across members.
        """
        members, error = self._selected_members(request.data)
        if error is not None:
            return error
        personalized = uses_personalization(
            str(request.data.get("body_html") or ""), str(request.data.get("body_text") or "")
        )
        resolution = EmailRecipientCollector.resolve(members, personalized=personalized)
        return Response(resolution.as_dict())

    @action(detail=False, methods=["post"])
    def recipient_count(self, request):
        """
        Get count of recipients for given selection criteria.

        POST /api/v1/emails/recipient_count/

        Request body:
        {
            "recipient_type": "all|group|individual|multiple",
            "recipient_group": 1,  // if type is "group"
            "recipient_member": 1   // if type is "individual"
        }
        """
        members, error = self._selected_members(request.data)
        if error is not None:
            return error
        resolution = EmailRecipientCollector.resolve(members)
        return Response({"count": len(resolution.recipients), "recipients": resolution.recipients})
