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

from doctors.models import Doctor, Patient, Appointment, DoctorAvailability


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
    
    # Get doctor availability for these dates
    availabilities = DoctorAvailability.objects.filter(
        date__in=all_dates,
        is_available=True
    ).select_related('doctor')
    
    # Group availability by date
    available_dates = {}
    for date in all_dates:
        available_dates[date] = []
    
    for availability in availabilities:
        if availability.date in available_dates:
            available_dates[availability.date].append(availability.doctor)
    
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
                status='confirmed'
            ).first()
            
            if existing_appointment:
                messages.error(request, 'This time slot is already booked. Please select another time.')
            else:
                # Create appointment
                appointment = Appointment.objects.create(
                    doctor=doctor,
                    patient=patient,
                    date=appointment_date,
                    start_time=appointment_time,
                    end_time=(datetime.combine(appointment_date, appointment_time) + timedelta(minutes=30)).time(),
                    status='confirmed'
                )
                
                messages.success(request, f'Appointment booked successfully with Dr. {doctor.first_name} {doctor.last_name} on {appointment_date.strftime("%B %d, %Y")} at {selected_time}')
                return redirect('patient:dashboard')
    
    # Handle doctor and date selection for slot generation
    selected_doctor_id = request.GET.get('doctor')
    selected_date_str = request.GET.get('date')
    
    available_slots = []
    if selected_doctor_id and selected_date_str:
        doctor = get_object_or_404(Doctor, id=selected_doctor_id)
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        
        # Check if doctor is available on this date
        is_available = DoctorAvailability.objects.filter(
            doctor=doctor,
            date=selected_date,
            is_available=True
        ).exists()
        
        if is_available:
            # Generate available slots with default working hours
            available_slots = generate_default_time_slots(selected_date)
            
            # Filter out booked appointments
            booked_times = Appointment.objects.filter(
                doctor=doctor,
                date=selected_date,
                status='confirmed'
            ).values_list('start_time', flat=True)
            
            # Filter out booked slots
            available_slots = [slot for slot in available_slots if slot['start_time'] not in booked_times]
    
    context = {
        'patient': patient,
        'available_doctors': available_doctors,
        'available_dates': available_dates,
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