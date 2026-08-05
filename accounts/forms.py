from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class SignUpForm(UserCreationForm):
    roll_number = forms.CharField(max_length=20)
    hostel = forms.CharField(max_length=50, required=False)

    class Meta:
        model = User
        fields = ["username", "email", "roll_number", "hostel", "password1", "password2"]