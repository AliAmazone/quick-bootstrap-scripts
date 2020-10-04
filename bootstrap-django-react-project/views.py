from django.shortcuts import render
from django.conf import settings


def index(request):
    context = dict(settings=settings)
    return render(request, "frontend/index.html", context)
