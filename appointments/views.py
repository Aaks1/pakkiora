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

from doctors.models import Doctor, DoctorTimeSlot, DoctorSchedule, Patient
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

    appointments = Appointment.objects.filter(
        patient=user
    ).select_related('doctor').order_by('-date', '-start_time')

    upcoming_appointments = appointments.filter(
        date__gte=today,
        status='BOOKED'
    )

    past_appointments = appointments.filter(
        date__lt=today
    )[:5]

    doctors = Doctor.objects.filter(
        is_active=True
    ).only('id', 'first_name', 'last_name', 'specialization')

    specializations = doctors.values_list('specialization', flat=True).distinct()

    # Generate slots for today if they don't exist
    schedule_service = ScheduleGeneratorService()
    for doctor in doctors:
        try:
            schedule_service.generate_daily_slots(doctor, today)
        except ValueError:
            # Doctor has no schedule for today, continue
            continue
    
    available_today = DoctorTimeSlot.objects.filter(
        date=today,
        status='available'
    ).count()

    context = {
        'patient': patient,
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments,
        'total_appointments': appointments.count(),
        'upcoming_count': upcoming_appointments.count(),
        'past_count': past_appointments.count(),
        'doctors': doctors,
        'specializations': list(specializations),
        'available_today': available_today,
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
# DOCTOR DETAIL + SLOTS
# -----------------------------
@login_required
def doctor_detail(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id, is_active=True)

    today = timezone.now().date()
    schedule_service = ScheduleGeneratorService()

    available_days = []

    for i in range(7):
        target_date = today + timedelta(days=i)

        try:
            schedule_service.generate_daily_slots(doctor, target_date)
        except ValueError:
            # Doctor has no schedule for this day, continue
            continue

        slot_count = DoctorTimeSlot.objects.filter(
            doctor=doctor,
            date=target_date,
            status='available'
        ).count()

        if slot_count > 0:
            available_days.append({
                'date': target_date,
                'available_slots': slot_count,
                'day_name': target_date.strftime('%A'),
                'formatted_date': target_date.strftime('%b %d'),
            })

    selected_date_str = request.GET.get('date')
    selected_date_slots = []

    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()

            selected_date_slots = DoctorTimeSlot.objects.filter(
                doctor=doctor,
                date=selected_date,
                status='available'
            ).order_by('start_datetime')

        except ValueError:
            pass

    return render(request, 'patient/doctors/doctor_profile_final.html', {
        'doctor': doctor,
        'available_days': available_days,
        'selected_date_slots': selected_date_slots,
        'today': today,
    })


# -----------------------------
# BOOK APPOINTMENT (SAFE)
# -----------------------------
@login_required
def book_appointment(request, doctor_id, date, start_time):
    doctor = get_object_or_404(Doctor, id=doctor_id, is_active=True)

    try:
        appointment_date = datetime.strptime(date, '%Y-%m-%d').date()
        appointment_time = datetime.strptime(start_time, '%H:%M').time()
    except ValueError:
        messages.error(request, "Invalid date or time format.")
        return redirect('patient:doctor_detail', doctor_id=doctor_id)

    if appointment_date < timezone.now().date():
        messages.error(request, "Cannot book past appointments.")
        return redirect('patient:doctor_detail', doctor_id=doctor_id)

    schedule_service = ScheduleGeneratorService()
    schedule_service.generate_daily_slots(doctor, appointment_date)

    try:
        slot = DoctorTimeSlot.objects.get(
            doctor=doctor,
            date=appointment_date,
            start_datetime__time=appointment_time,
            status='available'
        )
    except DoctorTimeSlot.DoesNotExist:
        messages.error(request, "Slot not available.")
        return redirect('patient:doctor_detail', doctor_id=doctor_id)

    if request.method == "POST":
        form = BookAppointmentForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    # Use select_for_update to prevent race conditions
                    slot = DoctorTimeSlot.objects.select_for_update().get(id=slot.id)
                    
                    if slot.status != 'available':
                        messages.error(request, "This time slot is already booked. Please choose another time.")
                        return redirect('patient:doctor_detail', doctor_id=doctor_id)

                    # Mark slot as booked
                    slot.status = 'booked'
                    slot.save(update_fields=['status'])

                    # Create appointment
                    Appointment.objects.create(
                        patient=request.user,
                        doctor=doctor,
                        date=appointment_date,
                        start_time=appointment_time,
                        end_time=(
                            datetime.combine(datetime.today(), appointment_time)
                            + timedelta(minutes=30)
                        ).time(),
                        symptoms=form.cleaned_data['symptoms'],
                        status='BOOKED'
                    )

                    messages.success(request, "Appointment booked successfully!")
                    return redirect('patient:dashboard')

            except DoctorTimeSlot.DoesNotExist:
                messages.error(request, "Slot not found. Please choose another time.")
                return redirect('patient:doctor_detail', doctor_id=doctor_id)
            except Exception as e:
                messages.error(request, "An error occurred while booking. Please try again.")
                return redirect('patient:doctor_detail', doctor_id=doctor_id)

    form = BookAppointmentForm()
    return render(request, 'patient/appointments/book.html', {
        'doctor': doctor,
        'date': appointment_date,
        'start_time': appointment_time,
        'form': form,
    })


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

            # Find and free up the slot using select_for_update
            try:
                slot = DoctorTimeSlot.objects.select_for_update().get(
                    doctor=appointment.doctor,
                    date=appointment.date,
                    start_datetime__time=appointment.start_time,
                    status='booked'
                )
                slot.status = 'available'
                slot.save(update_fields=['status'])
            except DoctorTimeSlot.DoesNotExist:
                # Slot might not exist, continue anyway
                pass

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