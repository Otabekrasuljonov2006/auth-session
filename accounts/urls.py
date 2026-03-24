from django.urls import path

from .views import (
    create_ticket_api,
    login_view,
    logout_view,
    profile_view,
    register_view,
    scan_ticket_api,
)

urlpatterns = [
    path("login/", login_view, name="login"),
    path("register/", register_view, name="register"),
    path("profile/", profile_view, name="profile"),
    path("logout/", logout_view, name="logout"),
    path("api/tickets/create/", create_ticket_api, name="create_ticket_api"),
    path("api/tickets/scan/", scan_ticket_api, name="scan_ticket_api"),
]
