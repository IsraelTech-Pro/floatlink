from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("staff/admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("staff/create-admin/", views.create_admin, name="create_admin"),
    path("staff/operations/", views.staff_operations, name="staff_operations"),
    path("staff/analytics/", views.staff_analytics, name="staff_analytics"),
]
