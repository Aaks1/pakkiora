"""
URL configuration for accounts app."""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Home/Landing Page
    path('', views.home, name='home'),
    
    # Authentication URLs
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile_view, name='profile'),
    path('logout/', views.logout_view, name='logout'),
    
    # Admin URLs
    path('admin/slots/', views.slot_generation_admin, name='slot_generation'),
]
