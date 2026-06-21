from django.urls import path
from crm import views

urlpatterns = [
    path("crm/clients/", views.client_list, name="client_list"),
    path("crm/clients/new/", views.client_create, name="client_create"),
    path("crm/clients/<int:pk>/", views.client_detail, name="client_detail"),
    path("crm/clients/<int:pk>/edit/", views.client_edit, name="client_edit"),
    path("crm/equipment/", views.equipment_list, name="equipment_list"),
    path("crm/equipment/new/", views.equipment_create, name="equipment_create"),
    path("crm/equipment/<int:pk>/", views.equipment_detail, name="equipment_detail"),
    path("crm/equipment/<int:pk>/edit/", views.equipment_edit, name="equipment_edit"),
]
