from django.contrib.auth.decorators import login_required
from django.urls import path

from . import views
from .views import ItemTableView
from django.shortcuts import redirect

app_name = 'inventory'
urlpatterns = [
    path('items/', ItemTableView.as_view(), name='items'),
    path('items/<int:pk>/edit/', login_required(views.ItemUpdateView.as_view()), name='item_edit'),
    path('items/new/', login_required(views.ItemCreateView.as_view()), name='item_create'),
    path('items/<int:pk>/delete/', login_required(views.ItemDeleteView.as_view()), name='item_delete'),
    path('', lambda request: redirect('inventory:items', permanent=False), name='home'),

]