from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.views.generic import ListView, DetailView

from datetime import datetime, timedelta

from doctors.models import Doctor, DoctorSchedule, Patient
from .models import Appointment
from .forms import BookAppointmentForm
from .schedule_generator import ScheduleGeneratorService


# -----------------------------
# PATIENT DASHBOARD (OPTIMIZED)
# -----------------------------
@login_required
def patient_dashboard(request):
    user = request.user
    today = timezone.now().date()

    patient, _ = Patient.objects.get_or_create(
        user=user,
        defaults={
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
        }
    )

    # Get selected date from query parameter
    selected_date_str = request.GET.get("date")
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = today
    else:
        selected_date = None

    # Get appointments for this patient
    appointments = Appointment.objects.filter(
        patient=patient
    ).select_related('doctor').order_by('-date', '-start_time')

    upcoming_appointments = appointments.filter(
        date__gte=today,
        status='confirmed'
    )

    past_appointments = appointments.filter(
        date__lt=today
    )[:5]

    # Get available doctors for selected date
    schedules = []
    if selected_date:
        from .utils import get_available_doctors
        schedules = get_available_doctors(selected_date)

    context = {
        'patient': patient,
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments,
        'total_appointments': appointments.count(),
        'upcoming_count': upcoming_appointments.count(),
        'past_count': past_appointments.count(),
        'selected_date': selected_date,
        'schedules': schedules,
        'today': today,
    }

    return render(request, 'patient/dashboard.html', context)


@login_required
def doctor_slots(request, doctor_id):
    """Show available slots for a specific doctor on a specific date"""
    from .utils import get_available_slots
    
    doctor = get_object_or_404(Doctor, id=doctor_id, is_active=True)
    
    selected_date_str = request.GET.get("date")
    if not selected_date_str:
        messages.error(request, "Please select a date first")
        return redirect('patient:dashboard')
    
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "Invalid date format")
        return redirect('patient:dashboard')
    
    # Check if date is in the past
    if selected_date < timezone.now().date():
        messages.error(request, "Cannot book appointments for past dates")
        return redirect('patient:dashboard')
    
    # Get available slots
    slots = get_available_slots(doctor, selected_date)
    
    context = {
        'doctor': doctor,
        'date': selected_date,
        'slots': slots,
    }
    
    return render(request, 'patient/slots.html', context)


@login_required
def book_appointment(request, doctor_id):
    """Book an appointment for a specific slot"""
    from .utils import book_appointment
    
    if request.method != "POST":
        return redirect('patient:dashboard')
    
    doctor = get_object_or_404(Doctor, id=doctor_id, is_active=True)
    patient = Patient.objects.get(user=request.user)
    
    date_str = request.POST.get('date')
    start_time_str = request.POST.get('start_time')
    end_time_str = request.POST.get('end_time')
    
    if not all([date_str, start_time_str, end_time_str]):
        messages.error(request, "Missing appointment details")
        return redirect('patient:dashboard')
    
    try:
        appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M:%S').time()
        end_time = datetime.strptime(end_time_str, '%H:%M:%S').time()
    except ValueError:
        messages.error(request, "Invalid date or time format")
        return redirect('patient:dashboard')
    
    # Check if date is in the past
    if appointment_date < timezone.now().date():
        messages.error(request, "Cannot book appointments for past dates")
        return redirect('patient:dashboard')
    
    # Book the appointment
    success, result = book_appointment(patient, doctor, appointment_date, start_time, end_time)
    
    if success:
        messages.success(request, f"Appointment booked successfully with Dr. {doctor.first_name} {doctor.last_name}")
    else:
        messages.error(request, str(result))
    
    return redirect('patient:dashboard')


# -----------------------------
# DOCTOR LIST
# -----------------------------
@login_required
def doctor_list(request):
    specialization = request.GET.get('specialization')

    doctors = Doctor.objects.filter(is_active=True)

    if specialization:
        doctors = doctors.filter(specialization__icontains=specialization)

    specializations = Doctor.objects.filter(
        is_active=True
    ).values_list('specialization', flat=True).distinct()

    return render(request, 'patient/doctors/list.html', {
        'doctors': doctors,
        'specializations': specializations,
        'specialization_filter': specialization,
    })


# -----------------------------
# DOCTOR DETAIL (LEGACY - KEPT FOR COMPATIBILITY)
# -----------------------------
@login_required
def doctor_detail(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id, is_active=True)
    
    # Redirect to new slot-based system
    today = timezone.now().date()
    return redirect('patient:doctor_slots', doctor_id=doctor_id) + f'?date={today.strftime("%Y-%m-%d")}'


# -----------------------------
# LEGACY BOOK APPOINTMENT (REDIRECT TO NEW SYSTEM)
# -----------------------------
@login_required
def book_appointment(request, doctor_id, date, start_time):
    # Redirect to new slot-based booking system
    return redirect('patient:doctor_slots', doctor_id=doctor_id) + f'?date={date}'


# -----------------------------
# APPOINTMENT DETAIL
# -----------------------------
@login_required
def appointment_detail(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        patient=request.user
    )

    if request.method == 'POST' and 'cancel_appointment' in request.POST:
        if appointment.status == 'BOOKED':
            appointment.status = 'CANCELLED'
            appointment.save()
            messages.success(request, "Appointment cancelled.")
        else:
            messages.error(request, "Cannot cancel this appointment.")

    return render(request, 'patient/appointments/detail.html', {
        'appointment': appointment
    })


# -----------------------------
# CANCEL APPOINTMENT
# -----------------------------
@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        patient=request.user,
        status='BOOKED'
    )

    if request.method == "POST":
        with transaction.atomic():
            # Mark appointment as cancelled
            appointment.status = "CANCELLED"
            appointment.save()

        messages.success(request, "Appointment cancelled successfully.")
        return redirect('patient:dashboard')

    return render(request, 'patient/appointments/cancel.html', {
        'appointment': appointment
    })


# -----------------------------
# CHANGE PASSWORD
# -----------------------------
@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)

        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password updated successfully.")
            return redirect('patient:profile')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'patient/change_password.html', {
        'form': form
    })


# -----------------------------
# PATIENT PROFILE
# -----------------------------
@login_required
def patient_profile(request):
    user = request.user
    
    patient, _ = Patient.objects.get_or_create(
        user=user,
        defaults={
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
        }
    )
    
    appointments = Appointment.objects.filter(
        patient=user
    ).count()
    
    context = {
        'patient': patient,
        'total_appointments': appointments,
    }
    
    return render(request, 'patient/profile.html', context)


@login_required
def past_appointments(request):
    """Show all patient appointments (past, present, cancelled)"""
    user = request.user
    
    # Get all appointments for this patient
    appointments = Appointment.objects.filter(
        patient=user
    ).select_related('doctor').order_by('-date', '-start_time')
    
    # Filter by status if requested
    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'all':
        appointments = appointments.filter(status=status_filter.upper())
    
    # Separate appointments by status for display
    upcoming_appointments = appointments.filter(
        date__gte=timezone.now().date(),
        status='BOOKED'
    )
    past_appointments = appointments.filter(
        date__lt=timezone.now().date()
    )
    cancelled_appointments = appointments.filter(status='CANCELLED')
    completed_appointments = appointments.filter(status='COMPLETED')
    no_show_appointments = appointments.filter(status='NO_SHOW')
    
    context = {
        'all_appointments': appointments,
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments,
        'cancelled_appointments': cancelled_appointments,
        'completed_appointments': completed_appointments,
        'no_show_appointments': no_show_appointments,
        'status_filter': status_filter or 'all',
        'total_count': appointments.count(),
    }
    
    return render(request, 'patient/past_appointments.html', context)


class AppointmentListView(ListView):
    """List patient's appointments"""
    model = Appointment
    template_name = 'patient/appointments/list.html'
    context_object_name = 'appointments'
    paginate_by = 20
    
    def get_queryset(self):
        return Appointment.objects.filter(
            patient=self.request.user
        ).select_related('doctor').order_by('-date', '-start_time')


class AppointmentDetailView(DetailView):
    """View appointment details"""
    model = Appointment
    template_name = 'patient/appointments/detail.html'
    pk_url_kwarg = 'appointment_id'
    
    def get_queryset(self):
        return Appointment.objects.filter(patient=self.request.user)