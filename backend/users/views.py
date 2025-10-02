from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from django.contrib.auth import get_user_model
from django.contrib.auth import update_session_auth_hash

from .serializers import UserSerializer, UserProfileSerializer, ChangePasswordSerializer

User = get_user_model()


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
