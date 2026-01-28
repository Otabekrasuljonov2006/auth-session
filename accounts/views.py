from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
# Create your views here.
@csrf_exempt
def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        if not username or not password:
            return HttpResponse("Qaysidir maydon bo'sh")
        if User.objects.filter(username = username).exists():
            return HttpResponse("Bu nomdagi foydalanuvchi avvaldan bor")
        User.objects.create_user(username = username, password=password)
        return redirect('login')
    return render(request, 'accounts/register.html')


@csrf_exempt
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username = username, password=password)
        if user is not None:
            login(request, user)
            return redirect('profile')
        return HttpResponse("Bunday foydalanuvchi mavjud emas")
    return render(request, 'accounts/login.html')

@csrf_exempt
@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html')
@csrf_exempt
def logout_view(request):
    logout(request)
    return redirect('login')
