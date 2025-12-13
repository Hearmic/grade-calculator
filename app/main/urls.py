from django.urls import path
from main import views
from django.views.generic.base import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage

urlpatterns = [
    path('', views.home, name='home'),
    path('calculate/', views.calculate_prediction, name='calculate_prediction'),
    path('health/', views.health_check, name='health_check'),
    path('ads.txt', RedirectView.as_view(url=staticfiles_storage.url('main/ads.txt'))),
]