"""
URL configuration for tire_workshop project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core.views import dashboard, warehouse, workshop_stock, update_product_stock, update_workshop_stock, suppliers

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', dashboard, name='dashboard'),
    path('warehouse/', warehouse, name='warehouse'),
    path('warehouse/update/<int:product_id>/', update_product_stock, name='update_product_stock'),
    path('workshop-stock/', workshop_stock, name='workshop_stock'),
    path('workshop-stock/update/<int:stock_id>/', update_workshop_stock, name='update_workshop_stock'),
    path('suppliers/', suppliers, name='suppliers'),
]
