class ExportAuditMixin:
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if getattr(self, "action", None) == "export_excel":
            from members.models import ExportAudit

            user = getattr(request, "user", None)
            object_id = str(self.kwargs.get("pk", ""))
            departments = getattr(self, "export_department_ids", None)
            if departments is None:
                requested = request.query_params.get("department", "")
                departments = [int(requested)] if requested.isdecimal() else []
            ExportAudit.objects.create(
                actor_id=user.pk if user and user.is_authenticated else None,
                object_type=self.queryset.model._meta.label_lower,
                object_id=int(object_id) if object_id.isdecimal() else None,
                department_ids=departments,
                status_code=response.status_code,
            )
            response["Cache-Control"] = "private, no-store"
        return response
