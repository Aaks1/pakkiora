"""
URL configuration for DoctorX project."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

import accounts.views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Accounts (Authentication)
    path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    
    # Admin Dashboard
    path('admin-dashboard/', accounts.views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/admins/', accounts.views.admin_list, name='admin_list'),
    path('admin-dashboard/admins/create/', accounts.views.admin_create, name='admin_create'),
    path('admin-dashboard/admins/<int:admin_id>/edit/', accounts.views.admin_edit, name='admin_edit'),
    path('admin-dashboard/admins/<int:admin_id>/delete/', accounts.views.admin_delete, name='admin_delete'),
    path('admin-dashboard/doctors/', accounts.views.doctor_list, name='doctor_list'),
    path('admin-dashboard/doctors/add/', accounts.views.add_doctor, name='add_doctor'),
    path('admin-dashboard/doctors/<int:doctor_id>/edit/', accounts.views.doctor_edit, name='doctor_edit'),
    path('admin-dashboard/doctors/<int:doctor_id>/delete/', accounts.views.doctor_delete, name='doctor_delete'),
    path('admin-dashboard/doctors/<int:doctor_id>/toggle/', accounts.views.doctor_toggle_active, name='doctor_toggle_active'),
    
        
    # Appointment Management
    path('admin-dashboard/appointments/', accounts.views.appointment_management, name='admin_appointment_management'),
    path('admin-dashboard/appointments/<int:appointment_id>/', accounts.views.appointment_detail_admin, name='admin_appointment_detail'),
    path('admin-dashboard/appointments/<int:appointment_id>/edit/', accounts.views.appointment_edit_admin, name='admin_appointment_edit'),
    path('admin-dashboard/appointments/<int:appointment_id>/cancel/', accounts.views.cancel_appointment_admin, name='admin_cancel_appointment'),
    path('admin-dashboard/doctors/<int:doctor_id>/appointments/', accounts.views.doctor_appointments, name='doctor_appointments'),
    path('admin-dashboard/slots/', accounts.views.slot_management, name='slot_management'),
    path('admin-dashboard/slots/<int:doctor_id>/edit/', accounts.views.slot_edit, name='slot_edit'),
    
    # User Management
    path('admin-dashboard/users/', accounts.views.user_management, name='user_management'),
    path('admin-dashboard/users/<int:user_id>/', accounts.views.user_detail_admin, name='user_detail'),
    path('admin-dashboard/users/<int:user_id>/edit/', accounts.views.user_edit_admin, name='user_edit'),
    path('admin-dashboard/users/<int:user_id>/toggle-active/', accounts.views.user_toggle_active_admin, name='user_toggle_active'),
    path('admin-dashboard/users/<int:user_id>/delete/', accounts.views.user_delete_admin, name='user_delete'),
    
    # Patient Appointments
    path('patient/', include(('appointments.urls', 'appointments'), namespace='patient')),
    
    # Home/Landing
    path('', accounts.views.home, name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
