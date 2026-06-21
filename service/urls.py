from django.urls import path
from service import views
from service import pdf_views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("requests/new/", views.request_create, name="request_create"),
    path("requests/<int:pk>/", views.request_detail, name="request_detail"),
    path("requests/<int:pk>/edit/", views.request_edit, name="request_edit"),
    path("requests/<int:pk>/assign/", views.request_assign_master, name="request_assign_master"),
    path("requests/<int:pk>/status/", views.request_change_status, name="request_change_status"),
    path("requests/<int:pk>/worklog/add/", views.worklog_add, name="worklog_add"),
    path("requests/<int:pk>/usage/add/", views.part_usage_add, name="part_usage_add"),
    path("requests/<int:pk>/reserve/", views.part_reserve_add, name="part_reserve_add"),
    path("requests/<int:pk>/pdf/", pdf_views.repair_request_pdf, name="repair_request_pdf"),

    path("parts/", views.parts_list, name="parts_list"),
    path("parts/new/", views.part_create, name="part_create"),
    path("parts/<int:part_id>/edit/", views.part_edit, name="part_edit"),

    path("reports/", views.reports, name="reports"),
    path("reports/pdf/", pdf_views.reports_pdf, name="reports_pdf"),

    path("notifications/", views.notifications_list, name="notifications_list"),
    path("notifications/<int:pk>/read/", views.notification_mark_read, name="notification_mark_read"),
    path("notifications/read-all/", views.notifications_read_all, name="notifications_read_all"),

    path("calendar/", views.master_calendar, name="master_calendar"),
]
