from django.contrib import admin
from django.urls import path
from .views import LoginView

urlpatterns = [
    path('', LoginView, name="login_panel"),
]
