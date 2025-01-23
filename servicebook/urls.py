from django.contrib.auth.decorators import login_required
from django.urls import path
from django.views.generic import RedirectView

from servicebook.views import (
    ServiceTableView,
    ServiceUpdateView,
    ServiceCreateView,
    AttendanceJsonView
)

app_name = 'servicebook'

urlpatterns = [
    # List view
    path('', ServiceTableView.as_view(), name='home'),
    
    # Service management
    path('new/', login_required(ServiceCreateView.as_view()), name='create'),
    path('<int:pk>/edit/', login_required(ServiceUpdateView.as_view()), name='edit'),
    
    # API endpoints for Ajax request from the Service edit page.
    path('<int:pk>/edit/attendance', login_required(AttendanceJsonView.as_view()), name='attendance_json'),
    
]