"""
URL configuration for Email Import Tool
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.email_import_home, name='email-import-home'),
]