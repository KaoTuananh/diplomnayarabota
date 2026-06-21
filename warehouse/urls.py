from django.urls import path
from warehouse import views

urlpatterns = [
    path("warehouse/suppliers/", views.supplier_list, name="supplier_list"),
    path("warehouse/suppliers/new/", views.supplier_create, name="supplier_create"),
    path("warehouse/suppliers/<int:pk>/edit/", views.supplier_edit, name="supplier_edit"),
    path("warehouse/purchases/", views.purchase_list, name="purchase_list"),
    path("warehouse/purchases/new/", views.purchase_create, name="purchase_create"),
    path("warehouse/purchases/<int:pk>/", views.purchase_detail, name="purchase_detail"),
    path("warehouse/purchases/<int:pk>/send/", views.purchase_send, name="purchase_send"),
    path("warehouse/purchases/<int:pk>/receive/", views.purchase_receive, name="purchase_receive"),
    path("warehouse/adjustments/", views.adjustment_list, name="adjustment_list"),
    path("warehouse/adjustments/new/", views.adjustment_create, name="adjustment_create"),
    path("warehouse/low-stock/", views.low_stock_list, name="low_stock_list"),
]
