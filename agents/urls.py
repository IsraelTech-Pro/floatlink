from django.urls import path

from . import views

app_name = "agents"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("update-gps/", views.update_gps, name="update_gps"),
]
