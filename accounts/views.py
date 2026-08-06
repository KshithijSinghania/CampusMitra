from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm
from django.conf import settings
from google_auth_oauthlib.flow import Flow
from .gmail_oauth import build_flow

def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.studentprofile.roll_number = form.cleaned_data["roll_number"]
            user.studentprofile.hostel = form.cleaned_data.get("hostel", "")
            user.studentprofile.save()

            username = form.cleaned_data.get("username")
            raw_password = form.cleaned_data.get("password1")
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect("gmail_connect")   # changed from "dashboard"
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

@login_required
def gmail_connect_view(request):
    flow = build_flow()

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    request.session["gmail_oauth_state"] = state
    request.session["gmail_code_verifier"] = flow.code_verifier

    return redirect(authorization_url)


@login_required
def gmail_callback_view(request):
    state = request.session["gmail_oauth_state"]

    flow = build_flow(state=state)
    flow.code_verifier = request.session["gmail_code_verifier"]

    flow.fetch_token(
        authorization_response=request.build_absolute_uri()
    )

    credentials = flow.credentials

    profile = request.user.studentprofile
    profile.gmail_refresh_token = credentials.refresh_token
    profile.gmail_linked = True
    profile.save()

    return redirect("dashboard")