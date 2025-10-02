from django.urls import path
from .views import SetupView, MigrationView

app_name = 'setup'

urlpatterns = [
    path('migrations/', MigrationView.as_view(), name='migrations'),
    path('', SetupView.as_view(), name='user_setup'),
]
