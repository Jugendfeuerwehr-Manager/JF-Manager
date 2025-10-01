from django.urls import path
from . import views
from .views_notifications import (
    notification_preferences, admin_notification_dashboard, notification_detail,
    retry_failed_notification, email_template_list, notification_stats_api,
    OrderSummaryView
)

app_name = 'orders'

urlpatterns = [
    # Bestellungen
    path('', views.OrderListView.as_view(), name='list'),
    path('create/', views.OrderCreateView.as_view(), name='create'),
    path('quick/', views.QuickOrderCreateView.as_view(), name='quick_create'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='detail'),
    path('<int:pk>/update/', views.OrderUpdateView.as_view(), name='update'),
    path('<int:pk>/quick-status/', views.quick_order_status_change, name='quick_status_change'),
    
    # Status Management
    path('<int:order_id>/item/<int:item_id>/status/', 
         views.update_order_item_status, 
         name='update_item_status'),
    
    # AJAX Endpoints
    path('api/item/<int:item_id>/sizes/', views.get_item_sizes, name='item_sizes'),
    
    # Bulk Operations
    path('bulk-status-update/', views.bulk_status_update, name='bulk_status_update'),
    
    # Analytics & Reports
    path('analytics/', views.order_analytics_dashboard, name='analytics'),
    path('export/', views.export_orders, name='export'),
    
    # Notifications
    path('notifications/preferences/', notification_preferences, name='notification_preferences'),
    path('notifications/dashboard/', admin_notification_dashboard, name='admin_notification_dashboard'),
    path('notifications/<int:log_id>/', notification_detail, name='notification_detail'),
    path('notifications/<int:log_id>/retry/', retry_failed_notification, name='retry_notification'),
    path('notifications/templates/', email_template_list, name='email_template_list'),
    path('api/notifications/stats/', notification_stats_api, name='notification_stats_api'),
    
    # Order Summary for External Personnel
    path('summary/send/', OrderSummaryView.as_view(), name='send_order_summary'),
]
