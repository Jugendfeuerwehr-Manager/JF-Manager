from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.contrib.auth import get_user_model

from .api_serializers import UserInfoSerializer, UserSerializer

User = get_user_model()


@extend_schema_view(
    list=extend_schema(summary="List all users", description="Get a paginated list of all users"),
    retrieve=extend_schema(summary="Get user details", description="Get detailed information about a specific user"),
    update=extend_schema(summary="Update user", description="Update user information"),
    partial_update=extend_schema(summary="Partially update user", description="Update specific user fields"),
)
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.prefetch_related('groups', 'user_permissions')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'email', 'date_joined']
    ordering = ['username']
    http_method_names = ['get', 'patch', 'head', 'options']  # No delete or full update

    def get_serializer_class(self):
        if self.action == 'me':
            return UserInfoSerializer
        elif self.action == 'retrieve':
            return UserInfoSerializer
        return UserSerializer

    @extend_schema(
        summary="Get current user info",
        description="Get complete information about the currently authenticated user including permissions and groups"
    )
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user information"""
        serializer = self.get_serializer(request.user, context={'request': request})
        return Response(serializer.data)
