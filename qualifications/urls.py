from django.urls import path
from . import views
from .autocomplete_views import user_autocomplete, member_autocomplete

app_name = 'qualifications'

urlpatterns = [
    # Dashboard
    path('', views.QualificationsDashboardView.as_view(), name='dashboard'),
    path('admin/', views.QualificationsAdminView.as_view(), name='admin'),
    
    # Qualifikationen
    path('qualifications/', views.QualificationsListView.as_view(), name='qualification_list'),
    path('qualifications/create/', views.QualificationCreateView.as_view(), name='qualification_create'),
    path('qualifications/<int:pk>/', views.QualificationDetailView.as_view(), name='qualification_detail'),
    path('qualifications/<int:pk>/edit/', views.QualificationUpdateView.as_view(), name='qualification_edit'),
    path('qualifications/<int:pk>/delete/', views.QualificationDeleteView.as_view(), name='qualification_delete'),
    
    # Qualifikationstypen
    path('qualification-types/', views.QualificationTypeListView.as_view(), name='qualification_type_list'),
    path('qualification-types/create/', views.QualificationTypeCreateView.as_view(), name='qualification_type_create'),
    path('qualification-types/<int:pk>/edit/', views.QualificationTypeUpdateView.as_view(), name='qualification_type_edit'),
    path('qualification-types/<int:pk>/delete/', views.QualificationTypeDeleteView.as_view(), name='qualification_type_delete'),
    
    # Sonderaufgaben
    path('special-tasks/', views.SpecialTasksListView.as_view(), name='special_task_list'),
    path('special-tasks/create/', views.SpecialTaskCreateView.as_view(), name='special_task_create'),
    path('special-tasks/<int:pk>/', views.SpecialTaskDetailView.as_view(), name='special_task_detail'),
    path('special-tasks/<int:pk>/edit/', views.SpecialTaskUpdateView.as_view(), name='special_task_edit'),
    path('special-tasks/<int:pk>/delete/', views.SpecialTaskDeleteView.as_view(), name='special_task_delete'),
    path('special-tasks/<int:pk>/end/', views.SpecialTaskEndView.as_view(), name='special_task_end'),
    
    # Sonderaufgaben-Typen
    path('special-task-types/', views.SpecialTaskTypeListView.as_view(), name='special_task_type_list'),
    path('special-task-types/create/', views.SpecialTaskTypeCreateView.as_view(), name='special_task_type_create'),
    path('special-task-types/<int:pk>/edit/', views.SpecialTaskTypeUpdateView.as_view(), name='special_task_type_edit'),
    path('special-task-types/<int:pk>/delete/', views.SpecialTaskTypeDeleteView.as_view(), name='special_task_type_delete'),
    
    # AJAX Endpoints
    path('api/qualification-type/<int:pk>/', views.qualification_type_details, name='qualification_type_details'),
    path('api/calculate-expiry/', views.calculate_expiry_date, name='calculate_expiry_date'),
    
    # Autocomplete endpoints
    path('autocomplete/users/', user_autocomplete, name='user_autocomplete'),
    path('autocomplete/members/', member_autocomplete, name='member_autocomplete'),
]
