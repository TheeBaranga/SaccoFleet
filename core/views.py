from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@require_GET
def home(request):
    return redirect("dashboard" if request.user.is_authenticated else "login")


@never_cache
@login_required
@require_GET
def dashboard(request):
    return render(request, "core/dashboard.html")


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})
