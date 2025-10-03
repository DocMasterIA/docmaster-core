from django.urls import path
from .views import LoginView, RegisterView, DashboardView, AreaDoUsuarioView, LogoutView

urlpatterns = [
    path('login', LoginView, name="login_panel"),
    path('logout', LogoutView, name="logout"),
    path('registro', RegisterView, name="registro_panel"),
    path('',DashboardView, name="dashboard"),
    path('area_do_usuario', AreaDoUsuarioView, name="area_do_usuario")
]
