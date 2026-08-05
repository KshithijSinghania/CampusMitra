from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm


def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # roll_number/hostel need to be saved onto the profile the signal just created
            user.studentprofile.roll_number = form.cleaned_data["roll_number"]
            user.studentprofile.hostel = form.cleaned_data.get("hostel", "")
            user.studentprofile.save()

            username = form.cleaned_data.get("username")
            raw_password = form.cleaned_data.get("password1")
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect("dashboard")
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            return render(request, "accounts/login.html", {"error": "Invalid username or password"})
    return render(request, "accounts/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard_view(request):
    return render(request, "accounts/dashboard.html")