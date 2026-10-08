from django.db.models import Q
from rest_framework import permissions, serializers, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError

from inventory.api.access import visible_item_department_ids
from members.models import Member


class RoleMemberOptionSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    department_ids = serializers.SerializerMethodField()

    def get_department_ids(self, member):
        ids = set(member.departments.values_list("pk", flat=True))
        allowed = getattr(self.context.get("view"), "_lookup_department_ids", None)
        return sorted(ids if allowed is None else ids & allowed)

    class Meta:
        model = Member
        fields = ["id", "full_name", "department_ids"]


class RoleMemberOptionsViewSet(viewsets.ReadOnlyModelViewSet):
    """Minimal person lookup for separate inventory and ordering capabilities."""

    serializer_class = RoleMemberOptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "head", "options"]
    queryset = Member.objects.all()

    def get_queryset(self):
        purpose = self.request.query_params.get("purpose")
        names = {
            "inventory": ["inventory.can_rent", "inventory.add_storagelocation"],
            "orders": ["orders.add_order", "orders.can_manage_orders"],
        }.get(purpose)
        if names is None:
            raise ValidationError({"purpose": "Inventar oder Bestellungen auswählen."})
        allowed = set()
        global_scope = False
        for name in names:
            area = visible_item_department_ids(self.request.user, name)
            if area is None:
                global_scope = True
            else:
                allowed |= area
        if not global_scope and not allowed:
            raise PermissionDenied("Keine Berechtigung zur fachlichen Personenauswahl.")
        raw = self.request.query_params.get("department")
        if raw:
            try:
                department_id = int(raw)
            except (TypeError, ValueError) as exc:
                raise ValidationError({"department": "Ungültige Abteilung."}) from exc
            if not global_scope and department_id not in allowed:
                raise PermissionDenied("Keine Personenauswahl für diese Abteilung.")
            allowed = {department_id}
            global_scope = False
        self._lookup_department_ids = None if global_scope else allowed
        queryset = Member.objects.all().prefetch_related("departments").order_by("lastname", "name", "pk")
        if not global_scope:
            queryset = queryset.filter(Q(departments__pk__in=allowed)).distinct()
        return queryset
