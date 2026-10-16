from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

@require_GET
def home(request):
    return render(request, "core/home.html")

@require_GET
def health(request):
    return JsonResponse({"status": "ok"})
