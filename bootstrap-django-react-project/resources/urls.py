from django.urls import re_path
from frontend import views


urlpatterns = [
    re_path(r'^.*/?$', views.index),
]
