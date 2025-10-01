from django.shortcuts import render
from django.http import request
# Create your views here.

def LoginView(request):
    return render(request,"login_portal.html")