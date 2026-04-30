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

from doctors.models import Doctor, Patient, Appointment


# -----------------------------
# PATIENT DASHBOARD (OPTIMIZED)
# -----------------------------
@login_required
def patient_dashboard(request):
    user = request.user
    today = timezone.now().date()

    patient, created = Patient.objects.get_or_create(
        user=user,
        defaults={
            "first_name": user.first_name or "Unknown",
            "last_name": user.last_name or "User",
        }
    )

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

    context = {
        'patient': patient,
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments,
        'total_appointments': appointments.count(),
        'upcoming_count': upcoming_appointments.count(),
        'past_count': past_appointments.count(),
        'today': today,
    }

    return render(request, 'patient/dashboard.html', context)






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