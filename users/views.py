from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from django.contrib.auth import get_user_model
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import PasswordResetView as DjangoPasswordResetView
from django.conf import settings
from django.http import HttpResponseRedirect
from urllib.parse import urlparse

from .serializers import UserSerializer, UserProfileSerializer, ChangePasswordSerializer

User = get_user_model()


class CustomPasswordResetView(DjangoPasswordResetView):
    """Overrides Django's PasswordResetView to use SITE_URL setting for the
    reset link domain.  When the app runs behind a reverse proxy the default
    behaviour (using request.get_host()) produces a localhost link.  Setting
    SITE_URL in the environment fixes this."""

    def form_valid(self, form):
        site_url = getattr(settings, 'SITE_URL', '')
        if site_url:
            parsed = urlparse(site_url)
            domain = parsed.netloc
            use_https = parsed.scheme == 'https'
            opts = {
                'use_https': use_https,
                'token_generator': self.token_generator,
                'from_email': self.from_email,
                'email_template_name': self.email_template_name,
                'subject_template_name': self.subject_template_name,
                'request': self.request,
                'html_email_template_name': self.html_email_template_name,
                'extra_email_context': self.extra_email_context,
                'domain_override': domain,
            }
            form.save(**opts)
            return HttpResponseRedirect(self.get_success_url())
        return super().form_valid(form)


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet für Benutzerverwaltung"""
    
    queryset = User.objects.all()
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication, TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Nur eigenes Profil für normale Benutzer"""
        if self.action == 'me':
            return User.objects.filter(id=self.request.user.id)
        return super().get_queryset()

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def me(self, request):
        """Endpoint für aktuelle Benutzerinformationen"""
        
        if request.method == 'GET':
            serializer = UserSerializer(request.user)
            return Response(serializer.data)
        
        elif request.method == 'PATCH':
            serializer = UserProfileSerializer(
                request.user, 
                data=request.data, 
                partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(UserSerializer(request.user).data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='change-password')
    def change_password(self, request):
        """Endpoint für Passwort-Änderung"""
        
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            # Update session auth hash to keep user logged in
            update_session_auth_hash(request, user)
            
            return Response({'message': 'Passwort erfolgreich geändert.'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
