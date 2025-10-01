from django.contrib import admin
from django.urls import path
from .views import LoginView, RegisterView

urlpatterns = [
    path('', LoginView, name="login_panel"),
    path('register', RegisterView, name="register_panel"),

]
