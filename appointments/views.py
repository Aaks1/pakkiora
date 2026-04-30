from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.views.generic import ListView, DetailView
from django.urls import reverse
from django.core.paginator import Paginator

from datetime import datetime, timedelta

from doctors.models import Doctor, Patient, DoctorAvailability
from appointments.models import Appointment


def parse_doctor_time_slots(doctor, selected_date):
    """Return normalized slot objects from doctor's configured time slots."""
    raw_slots = [s.strip() for s in (doctor.time_slots or '').split(',') if s.strip()]
    parsed_slots = []
    for slot in raw_slots:
        try:
            start_time = datetime.strptime(slot, '%H:%M').time()
            end_time = (datetime.combine(selected_date, start_time) + timedelta(minutes=30)).time()
            parsed_slots.append({
                'start_time': start_time,
                'end_time': end_time,
                'start_str': datetime.combine(selected_date, start_time).strftime('%I:%M %p'),
                'end_str': datetime.combine(selected_date, end_time).strftime('%I:%M %p'),
            })
        except ValueError:
            continue
    return parsed_slots


def is_doctor_available_on_date(doctor, selected_date):
    """Use explicit availability override when present, else doctor day configuration."""
    override = DoctorAvailability.objects.filter(doctor=doctor, date=selected_date).first()
    if override:
        return override.is_available
    return selected_date.strftime('%A').lower() in (doctor.available_days or [])


def generate_default_time_slots(date):
    """Generate time slots for a specific date using default working hours"""
    slots = []
    
    # Default working hours: 9:00 AM - 5:00 PM
    start_time = datetime.strptime('09:00', '%H:%M').time()
    end_time = datetime.strptime('17:00', '%H:%M').time()
    slot_duration = 30  # minutes
    
    current_time = datetime.combine(date, start_time)
    end_datetime = datetime.combine(date, end_time)
    
    while current_time < end_datetime:
        slot_end = current_time + timedelta(minutes=slot_duration)
        if slot_end <= end_datetime:
            slots.append({
                'start_time': current_time.time(),
                'end_time': slot_end.time(),
                'start_str': current_time.strftime('%I:%M %p'),
                'end_str': slot_end.strftime('%I:%M %p')
            })
        current_time = slot_end
    
    return slots


# -----------------------------
# PATIENT DASHBOARD (OPTIMIZED)
# -----------------------------
@login_required
def patient_dashboard(request):
    """Patient dashboard aligned with booking flow."""
    patient, _ = Patient.objects.get_or_create(
        user=request.user,
        defaults={
            "first_name": request.user.first_name or "Unknown",
            "last_name": request.user.last_name or "User",
        }
    )

    today = timezone.now().date()
    appointments = Appointment.objects.filter(patient=request.user).select_related('doctor')
    upcoming_appointments = appointments.filter(date__gte=today, status='BOOKED').order_by('date', 'start_time')[:5]
    recent_appointments = appointments.order_by('-date', '-start_time')[:5]
    doctor_search = request.GET.get('doctor_search', '').strip()
    available_doctors_qs = Doctor.objects.filter(is_active=True)
    if doctor_search:
        available_doctors_qs = available_doctors_qs.filter(
            Q(first_name__icontains=doctor_search) |
            Q(last_name__icontains=doctor_search) |
            Q(specialization__icontains=doctor_search) |
            Q(department__icontains=doctor_search)
        )

    available_doctors_qs = available_doctors_qs.order_by('first_name', 'last_name')
    doctors_paginator = Paginator(available_doctors_qs, 6)
    doctor_page = request.GET.get('doctor_page')
    available_doctors = doctors_paginator.get_page(doctor_page)

    context = {
        "patient": patient,
        "total_appointments": appointments.count(),
        "upcoming_count": appointments.filter(date__gte=today, status='BOOKED').count(),
        "completed_count": appointments.filter(status='COMPLETED').count(),
        "cancelled_count": appointments.filter(status='CANCELLED').count(),
        "upcoming_appointments": upcoming_appointments,
        "recent_appointments": recent_appointments,
        "available_doctors": available_doctors,
        "doctor_search": doctor_search,
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
    """Doctor detail page with booking functionality"""
    doctor = get_object_or_404(Doctor, id=doctor_id, is_active=True)
    
    # Get patient
    patient, _ = Patient.objects.get_or_create(
        user=request.user,
        defaults={
            "first_name": request.user.first_name or "Unknown",
            "last_name": request.user.last_name or "User",
        }
    )
    
    # Get current and next week dates
    today = timezone.now().date()
    current_week_start = today - timedelta(days=today.weekday())
    current_week_end = current_week_start + timedelta(days=6)
    next_week_start = current_week_start + timedelta(days=7)
    next_week_end = next_week_start + timedelta(days=6)
    
    # Get available dates for this doctor
    all_dates = []
    for i in range(14):  # Current week + next week
        date = current_week_start + timedelta(days=i)
        if date >= today:
            all_dates.append(date)
    
    # Build availability from doctor configured days + overrides
    availabilities = []
    for date in all_dates:
        if is_doctor_available_on_date(doctor, date):
            availabilities.append(type('obj', (), {'date': date}))
    
    # Get doctor's appointments for availability checking
    doctor_appointments = Appointment.objects.filter(
        doctor=doctor,
        date__in=[availability.date for availability in availabilities],
        status='BOOKED'
    ).select_related('patient')
    
    context = {
        'doctor': doctor,
        'patient': patient,
        'availabilities': availabilities,
        'doctor_appointments': doctor_appointments,
        'today': today,
        'current_week_start': current_week_start,
        'current_week_end': current_week_end,
        'next_week_start': next_week_start,
        'next_week_end': next_week_end,
    }
    
    return render(request, 'patient/doctors/detail.html', context)


# -----------------------------
# DOCTOR-SPECIFIC BOOKING (Piki Ora Style)
# -----------------------------
@login_required
def doctor_book_appointment(request, doctor_id):
    """Doctor-specific route redirects to unified booking flow."""
    return redirect(f"{reverse('patient:book_appointment')}?doctor={doctor_id}")


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


@login_required
def edit_appointment(request, appointment_id):
    """Allow patient to edit date/time for booked appointments."""
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        patient=request.user,
        status='BOOKED'
    )

    doctor = appointment.doctor
    today = timezone.now().date()

    if request.method == 'POST':
        selected_date = request.POST.get('date')
        selected_time = request.POST.get('time')

        if selected_date and selected_time:
            appointment_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            appointment_time = datetime.strptime(selected_time, '%H:%M').time()

            if appointment_date < today:
                messages.error(request, 'Appointment date cannot be in the past.')
            else:
                with transaction.atomic():
                    conflict = Appointment.objects.select_for_update().filter(
                        doctor=doctor,
                        date=appointment_date,
                        start_time=appointment_time,
                        status='BOOKED'
                    ).exclude(id=appointment.id).exists()

                    if conflict:
                        messages.error(request, 'This slot is already booked. Please pick another time.')
                    else:
                        appointment.date = appointment_date
                        appointment.start_time = appointment_time
                        appointment.end_time = (datetime.combine(appointment_date, appointment_time) + timedelta(minutes=30)).time()
                        appointment.save(update_fields=['date', 'start_time', 'end_time', 'updated_at'])
                        messages.success(request, 'Appointment updated successfully.')
                        return redirect('patient:past_appointments')
        else:
            messages.error(request, 'Please select both date and time.')

    # Next 30 days availability for current doctor
    available_dates = []
    for i in range(0, 30):
        date_candidate = today + timedelta(days=i)
        if is_doctor_available_on_date(doctor, date_candidate):
            available_dates.append(date_candidate)

    selected_date_str = request.GET.get('date') or request.POST.get('date') or appointment.date.strftime('%Y-%m-%d')
    selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()

    available_slots = []
    if is_doctor_available_on_date(doctor, selected_date):
        available_slots = parse_doctor_time_slots(doctor, selected_date) or generate_default_time_slots(selected_date)
        booked_times = Appointment.objects.filter(
            doctor=doctor,
            date=selected_date,
            status='BOOKED'
        ).exclude(id=appointment.id).values_list('start_time', flat=True)
        available_slots = [slot for slot in available_slots if slot['start_time'] not in booked_times]

    return render(request, 'patient/appointments/edit.html', {
        'appointment': appointment,
        'doctor': doctor,
        'available_dates': available_dates,
        'available_slots': available_slots,
        'selected_date_str': selected_date_str,
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
    
    appointments_qs = Appointment.objects.filter(patient=user)
    appointments = appointments_qs.count()
    upcoming_appointments = appointments_qs.filter(date__gte=timezone.now().date(), status='BOOKED').count()
    my_doctors = Doctor.objects.filter(patient_appointments__patient=user).distinct()[:6]
    
    context = {
        'patient': patient,
        'total_appointments': appointments,
        'upcoming_appointments': upcoming_appointments,
        'my_doctors': my_doctors,
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


@login_required
def book_appointment(request):
    """Patient appointment booking with automatic slot generation"""
    today = timezone.now().date()
    
    # Get patient
    patient, _ = Patient.objects.get_or_create(
        user=request.user,
        defaults={
            "first_name": request.user.first_name or "Unknown",
            "last_name": request.user.last_name or "User",
        }
    )
    
    # Get available doctors
    available_doctors = Doctor.objects.filter(is_active=True)
    
    # Get current and next week dates
    current_week_start = today - timedelta(days=today.weekday())
    current_week_end = current_week_start + timedelta(days=6)
    next_week_start = current_week_start + timedelta(days=7)
    next_week_end = next_week_start + timedelta(days=6)
    
    # Get available dates for all doctors
    all_dates = []
    for i in range(14):  # Current week + next week
        date = current_week_start + timedelta(days=i)
        if date >= today:
            all_dates.append(date)
    
    # Group available doctors by date from doctor config + explicit overrides.
    available_dates = {date: [] for date in all_dates}
    for doctor in available_doctors:
        for date in all_dates:
            if is_doctor_available_on_date(doctor, date):
                available_dates[date].append(doctor)
    
    # Handle form submissions
    if request.method == 'POST':
        doctor_id = request.POST.get('doctor')
        selected_date = request.POST.get('date')
        selected_time = request.POST.get('time')
        
        if doctor_id and selected_date and selected_time:
            doctor = get_object_or_404(Doctor, id=doctor_id)
            appointment_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            appointment_time = datetime.strptime(selected_time, '%H:%M').time()
            
            # Check if time slot is available
            existing_appointment = Appointment.objects.filter(
                doctor=doctor,
                date=appointment_date,
                start_time=appointment_time,
                status='BOOKED'
            ).first()
            
            if existing_appointment:
                messages.error(request, 'This time slot is already booked. Please select another time.')
            else:
                # Create appointment
                appointment = Appointment.objects.create(
                    doctor=doctor,
                    patient=request.user,
                    date=appointment_date,
                    start_time=appointment_time,
                    end_time=(datetime.combine(appointment_date, appointment_time) + timedelta(minutes=30)).time(),
                    status='BOOKED'
                )
                
                messages.success(request, f'Appointment booked successfully with Dr. {doctor.first_name} {doctor.last_name} on {appointment_date.strftime("%B %d, %Y")} at {selected_time}')
                return redirect('patient:doctors')
    
    # Handle doctor and date selection for slot generation
    selected_doctor_id = request.GET.get('doctor')
    selected_date_str = request.GET.get('date')
    selected_doctor = None
    if selected_doctor_id:
        selected_doctor = get_object_or_404(Doctor, id=selected_doctor_id, is_active=True)
        available_dates = {date: [selected_doctor] for date in all_dates if is_doctor_available_on_date(selected_doctor, date)}
    
    available_slots = []
    if selected_doctor_id and selected_date_str:
        doctor = get_object_or_404(Doctor, id=selected_doctor_id)
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        
        # Check if doctor is available on this date
        is_available = is_doctor_available_on_date(doctor, selected_date)
        
        if is_available:
            available_slots = parse_doctor_time_slots(doctor, selected_date) or generate_default_time_slots(selected_date)
            
            # Filter out booked appointments
            booked_times = Appointment.objects.filter(
                doctor=doctor,
                date=selected_date,
                status='BOOKED'
            ).values_list('start_time', flat=True)
            
            # Filter out booked slots
            available_slots = [slot for slot in available_slots if slot['start_time'] not in booked_times]
    
    context = {
        'patient': patient,
        'available_doctors': available_doctors,
        'available_dates': available_dates,
        'selected_doctor': selected_doctor,
        'available_slots': available_slots,
        'selected_doctor_id': selected_doctor_id,
        'selected_date_str': selected_date_str,
        'today': today,
        'current_week_start': current_week_start,
        'current_week_end': current_week_end,
        'next_week_start': next_week_start,
        'next_week_end': next_week_end,
    }
    
    return render(request, 'patient/book_appointment.html', context)