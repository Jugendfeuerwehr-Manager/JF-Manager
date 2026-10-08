from django.http import HttpResponseForbidden, JsonResponse
from django.urls import Resolver404, resolve

from .access import FORBIDDEN_CODE, FORBIDDEN_DETAIL, is_portal_account, portal_route_allowed


class PortalBoundaryMiddleware:
    """Keep portal accounts out of every staff route (PORTAL-01.2).

    Runs before any view, so views that override ``permission_classes`` or are
    not DRF views cannot let a portal account through.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not is_portal_account(getattr(request, "user", None)):
            return self.get_response(request)
        try:
            match = resolve(request.path_info)
        except Resolver404:
            return self.get_response(request)
        if portal_route_allowed(match):
            return self.get_response(request)
        if request.path_info.startswith("/api/"):
            return JsonResponse({"detail": FORBIDDEN_DETAIL, "code": FORBIDDEN_CODE}, status=403)
        return HttpResponseForbidden(FORBIDDEN_DETAIL)
