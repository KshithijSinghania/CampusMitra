from django.contrib import admin
from .models import MessTiming, Contact


@admin.register(MessTiming)
class MessTimingAdmin(admin.ModelAdmin):
    list_display = ["hall", "meal", "start_time", "end_time"]
    list_filter = ["hall", "meal"]


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ["name", "department", "designation", "phone", "email"]
    search_fields = ["name", "department"]

from .models import MessTiming, Contact, HumanEscalation


@admin.register(HumanEscalation)
class HumanEscalationAdmin(admin.ModelAdmin):
    list_display = ["question", "user", "created_at", "resolved"]
    list_filter = ["resolved"]