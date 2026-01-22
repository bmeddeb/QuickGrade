"""
Core app URL configuration.
"""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("profile/", views.profile, name="profile"),
    path("preferences/", views.preferences, name="preferences"),
    path("upload/", views.upload, name="upload"),
]
