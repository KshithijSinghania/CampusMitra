from django.urls import path
from . import views

urlpatterns = [
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("gmail/connect/", views.gmail_connect_view, name="gmail_connect"),
    path("gmail/callback/", views.gmail_callback_view, name="gmail_callback"),
]