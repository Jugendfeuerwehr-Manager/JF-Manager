from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Bestellungen
    path('', views.OrderListView.as_view(), name='list'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='detail'),
    path('create/', views.OrderCreateView.as_view(), name='create'),
    path('quick/', views.QuickOrderCreateView.as_view(), name='quick_create'),
    
    # Status Management
    path('<int:order_id>/item/<int:item_id>/status/', 
         views.update_order_item_status, 
         name='update_item_status'),
    
    # AJAX Endpoints
    path('api/item/<int:item_id>/sizes/', views.get_item_sizes, name='item_sizes'),
]
