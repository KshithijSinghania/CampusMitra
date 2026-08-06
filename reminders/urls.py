from django.urls import path
from . import views

urlpatterns = [
    path("", views.reminder_list_view, name="reminder_list"),
    path("<int:pk>/delete/", views.reminder_delete_view, name="reminder_delete"),
]