from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('use-material/', views.use_material, name='use_material'),
    path('logout/', views.logout_confirm, name='logout'),
]
