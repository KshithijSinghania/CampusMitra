from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import StudentProfile


class SignupFlowTests(TestCase):
    def test_signup_creates_user_and_profile(self):
        response = self.client.post(reverse("signup"), {
            "username": "teststudent",
            "email": "test@iiti.ac.in",
            "roll_number": "22CS1234",
            "hostel": "H10",
            "password1": "StrongPass!123",
            "password2": "StrongPass!123",
        })
        # successful signup should redirect (302), not re-render the form (200)
        self.assertEqual(response.status_code, 302)

        # user should exist
        self.assertTrue(User.objects.filter(username="teststudent").exists())

        # profile should exist and hold the roll number
        user = User.objects.get(username="teststudent")
        self.assertEqual(user.studentprofile.roll_number, "22CS1234")

    def test_signup_logs_user_in_automatically(self):
        self.client.post(reverse("signup"), {
            "username": "teststudent2",
            "email": "test2@iiti.ac.in",
            "roll_number": "22CS5678",
            "hostel": "",
            "password1": "StrongPass!123",
            "password2": "StrongPass!123",
        })
        # dashboard is @login_required — if signup logged us in, this should load (200)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_requires_login(self):
        # logging out first, then trying to hit the dashboard directly
        response = self.client.get(reverse("dashboard"))
        # should redirect to login, not show the dashboard
        self.assertEqual(response.status_code, 302)

    def test_login_with_correct_credentials(self):
        User.objects.create_user(username="existinguser", password="StrongPass!123")
        response = self.client.post(reverse("login"), {
            "username": "existinguser",
            "password": "StrongPass!123",
        })
        self.assertEqual(response.status_code, 302)

    def test_login_with_wrong_password_fails(self):
        User.objects.create_user(username="existinguser2", password="StrongPass!123")
        response = self.client.post(reverse("login"), {
            "username": "existinguser2",
            "password": "WrongPassword",
        })
        # wrong credentials should re-render the login page (200), not redirect
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password")

    def test_logout_ends_session(self):
        User.objects.create_user(username="existinguser3", password="StrongPass!123")
        self.client.login(username="existinguser3", password="StrongPass!123")
        self.client.get(reverse("logout"))
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)  # logged out → dashboard redirects again