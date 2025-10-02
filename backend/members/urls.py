from django.contrib.auth.decorators import login_required
from django.urls import path
from typing import List

from .views import (
    MemberCreateView,
    MemberDeleteView,
    MemberDetailView,
    MemberExcelApiView,
    MemberRentView,
    MemberTableView,
    MemberUpdateView,
    ParentCreateView,
    ParentDeleteView,
    ParentTableView,
    ParentUpdateView,
)

app_name = 'members'

# Member management URLs
member_patterns: List[path] = [
    path('', MemberTableView.as_view(), name='index'),
    path('new/', login_required(MemberCreateView.as_view()), name='create'),
    path('<int:pk>/', MemberDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', login_required(MemberUpdateView.as_view()), name='edit'),
    path('<int:pk>/delete/', login_required(MemberDeleteView.as_view()), name='delete'),
    path('<int:pk>/rent/', MemberRentView.as_view(), name='rent'),
]

# Parent management URLs
parent_patterns: List[path] = [
    path('parents/', ParentTableView.as_view(), name='parents'),
    path('parents/new/', login_required(ParentCreateView.as_view()), name='parent_create'),
    path('parents/<int:pk>/edit/', login_required(ParentUpdateView.as_view()), name='parent_edit'),
    path('parents/<int:pk>/delete/', login_required(ParentDeleteView.as_view()), name='parent_delete'),
]

# API URLs
api_patterns: List[path] = [
    path('members.xlsx', MemberExcelApiView.as_view(), name='members_export'),
]

# Combine all URL patterns
urlpatterns = member_patterns + parent_patterns + api_patterns