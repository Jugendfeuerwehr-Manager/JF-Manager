from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .api_serializers import (
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserInfoSerializer,
    UserSerializer,
)
from .tokens import password_reset_token

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
    # Allow POST so custom POST actions (e.g. request_password_reset, reset_password,
    # change_password) are reachable while still avoiding DELETE/PUT
    http_method_names = ['get', 'patch', 'post', 'head', 'options']  # No delete or full update

    def get_serializer_class(self):
        if self.action in ['me', 'retrieve', 'update', 'partial_update']:
            return UserInfoSerializer
        return UserSerializer

    @extend_schema(
        summary="Get or update current user info",
        description="GET: current user information. PATCH: update current user profile fields."
    )
    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        """Get or partially update current user information"""
        if request.method == 'PATCH':
            serializer = self.get_serializer(
                request.user, data=request.data, partial=True, context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        serializer = self.get_serializer(request.user, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Request password reset",
        description="Request a password reset email. If the email exists, a reset link will be sent.",
        request=PasswordResetRequestSerializer,
        responses={200: {'description': 'Password reset email sent if user exists'}}
    )
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def request_password_reset(self, request):
        """
        Request password reset by email.
        Returns success even if email doesn't exist (security best practice).
        """
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email, is_active=True)

            # Generate token and uid
            token = password_reset_token.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # Build reset URL (frontend URL)
            reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"

            # Send email
            context = {
                'user': user,
                'reset_url': reset_url,
                'site_name': 'JF-Manager'
            }

            subject = 'Password Reset Request - JF-Manager'
            html_message = render_to_string('users/password_reset_email.html', context)
            plain_message = strip_tags(html_message)

            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=False,
            )
        except User.DoesNotExist:
            # Don't reveal that user doesn't exist
            pass

        # Always return success for security
        return Response({
            'message': 'If an account exists with this email, you will receive password reset instructions.'
        }, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Confirm password reset",
        description="Reset password using token from email",
        request=PasswordResetConfirmSerializer,
        responses={
            200: {'description': 'Password successfully reset'},
            400: {'description': 'Invalid token or passwords do not match'}
        }
    )
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def reset_password(self, request):
        """Reset password using token from email"""
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Decode user ID
            uid = force_str(urlsafe_base64_decode(serializer.validated_data['uid']))
            user = User.objects.get(pk=uid)

            # Verify token
            if not password_reset_token.check_token(user, serializer.validated_data['token']):
                return Response({
                    'error': 'Invalid or expired reset token.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Set new password
            user.set_password(serializer.validated_data['new_password'])
            user.save()

            return Response({
                'message': 'Password has been reset successfully.'
            }, status=status.HTTP_200_OK)

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({
                'error': 'Invalid reset link.'
            }, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Change password",
        description="Change password for authenticated user",
        request=PasswordChangeSerializer,
        responses={
            200: {'description': 'Password successfully changed'},
            400: {'description': 'Invalid old password or passwords do not match'}
        }
    )
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """Change password for logged in user"""
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # Set new password
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()

        return Response({
            'message': 'Password has been changed successfully.'
        }, status=status.HTTP_200_OK)
