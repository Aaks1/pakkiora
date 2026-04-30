from django.urls import path
from . import views

app_name = 'patient'

urlpatterns = [
    # Patient Dashboard
    path('', views.patient_dashboard, name='dashboard'),
    
    # Doctors
    path('doctors/', views.doctor_list, name='doctors'),
    path('doctors/<int:doctor_id>/', views.doctor_detail, name='doctor_detail'),
    
    # Appointment Booking
    path('appointments/book/<int:doctor_id>/<str:date>/<str:start_time>/', views.book_appointment, name='book_appointment'),
    path('appointments/<int:appointment_id>/', views.appointment_detail, name='appointment_detail'),
    
    # Profile
    path('profile/', views.patient_profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Appointments
    path('appointments/', views.past_appointments, name='past_appointments'),
]