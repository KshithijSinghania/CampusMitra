from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Reminder
from .forms import ReminderForm


@login_required
def reminder_list_view(request):
    if request.method == "POST":
        form = ReminderForm(request.POST)
        if form.is_valid():
            reminder = form.save(commit=False)
            reminder.user = request.user
            reminder.save()
            return redirect("reminder_list")
    else:
        form = ReminderForm()

    reminders = request.user.reminders.all()  # uses the related_name from Phase 3.1
    return render(request, "reminders/reminder_list.html", {"form": form, "reminders": reminders})


@login_required
def reminder_delete_view(request, pk):
    reminder = get_object_or_404(Reminder, pk=pk, user=request.user)  # user=request.user prevents deleting someone else's reminder
    reminder.delete()
    return redirect("reminder_list")