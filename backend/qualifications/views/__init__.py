from .dashboard_views import QualificationsDashboardView, QualificationsListView, SpecialTasksListView, QualificationsAdminView
from .qualification_views import (
    QualificationCreateView, QualificationUpdateView, QualificationDeleteView, 
    QualificationDetailView, QualificationTypeCreateView, QualificationTypeUpdateView,
    QualificationTypeListView, QualificationTypeDeleteView,
    qualification_type_details, calculate_expiry_date
)
from .special_task_views import (
    SpecialTaskCreateView, SpecialTaskUpdateView, SpecialTaskDeleteView,
    SpecialTaskDetailView, SpecialTaskEndView, SpecialTaskTypeCreateView,
    SpecialTaskTypeUpdateView, SpecialTaskTypeListView, SpecialTaskTypeDeleteView
)

__all__ = [
    'QualificationsDashboardView',
    'QualificationsAdminView',
    'QualificationsListView',
    'SpecialTasksListView',
    'QualificationCreateView',
    'QualificationUpdateView',
    'QualificationDeleteView',
    'QualificationDetailView',
    'QualificationTypeCreateView',
    'QualificationTypeUpdateView',
    'QualificationTypeListView',
    'QualificationTypeDeleteView',
    'SpecialTaskCreateView',
    'SpecialTaskUpdateView',
    'SpecialTaskDeleteView',
    'SpecialTaskDetailView',
    'SpecialTaskEndView',
    'SpecialTaskTypeCreateView',
    'SpecialTaskTypeUpdateView',
    'SpecialTaskTypeListView',
    'SpecialTaskTypeDeleteView',
    'qualification_type_details',
    'calculate_expiry_date',
]
