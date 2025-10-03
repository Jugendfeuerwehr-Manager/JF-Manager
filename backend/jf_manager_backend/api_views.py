from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from dynamic_preferences.registries import global_preferences_registry


class AppSettingsView(APIView):
    """
    API endpoint to retrieve application settings
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get application settings",
        description="Get public application settings like app name, contact emails, etc."
    )
    def get(self, request):
        global_preferences = global_preferences_registry.manager()
        
        # Extract relevant settings - adjust based on your dynamic_preferences_registry
        settings = {
            'app_name': getattr(global_preferences.get('general__app_name', None), 'value', 'JF-Manager') if hasattr(global_preferences, 'general__app_name') else 'JF-Manager',
            'organization_name': getattr(global_preferences.get('general__organization_name', None), 'value', '') if hasattr(global_preferences, 'general__organization_name') else '',
            'contact_email': getattr(global_preferences.get('general__contact_email', None), 'value', '') if hasattr(global_preferences, 'general__contact_email') else '',
            'equipment_manager_email': getattr(global_preferences.get('general__equipment_manager_email', None), 'value', '') if hasattr(global_preferences, 'general__equipment_manager_email') else '',
        }
        
        return Response(settings)
