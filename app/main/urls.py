from django.urls import path
from main import views

urlpatterns = [
    path('', views.home, name='home'),
    path('calculate/', views.calculate_prediction, name='calculate_prediction'),
    path('health/', views.health_check, name='health_check'),
]