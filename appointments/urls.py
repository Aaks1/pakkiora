from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    # Patient Dashboard
    path('', views.patient_dashboard, name='dashboard'),
    
    # Doctors
    path('doctors/', views.doctor_list, name='doctors'),
    path('doctors/<int:doctor_id>/', views.doctor_detail, name='doctor_detail'),
    
        
    # Legacy Appointments (kept for compatibility)
    path('appointments/', views.past_appointments, name='past_appointments'),
    path('appointments/<int:appointment_id>/', views.appointment_detail, name='appointment_detail'),
    path('appointments/<int:appointment_id>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    path('appointments/list/', views.AppointmentListView.as_view(), name='appointment_list'),
    
    # Profile
    path('profile/', views.patient_profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
]