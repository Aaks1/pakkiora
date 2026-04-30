from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.generic import ListView, DetailView
from django.urls import reverse
from django.db import models, transaction
from doctors.models import Doctor, DoctorTimeSlot
from .models import Appointment
from .forms import AppointmentForm, BookAppointmentForm
from .schedule_generator import ScheduleGeneratorService

@login_required
def patient_dashboard(request):
    """Patient dashboard with optimized queries"""
    user = request.user
    
    # Get or create patient profile
    from doctors.models import Patient
    try:
        patient = Patient.objects.select_related('user').get(user=user)
    except Patient.DoesNotExist:
        # Create patient profile if it doesn't exist
        patient = Patient.objects.create(
            user=user,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email
        )
    
    # Optimized queries with single database hit
    today = timezone.now().date()
    
    # Get all appointments in one query
    all_appointments = Appointment.objects.filter(
        patient=user
    ).select_related('doctor').order_by('-date', '-start_time')
    
    # Separate upcoming and past appointments
    upcoming_appointments = [apt for apt in all_appointments if apt.date >= today and apt.status == 'BOOKED']
    past_appointments = [apt for apt in all_appointments if apt.date < today][:5]
    
    # Get available doctors with prefetch
    doctors = Doctor.objects.filter(is_active=True).only('id', 'first_name', 'last_name', 'specialization')
    
    # Get specializations efficiently
    specializations = list(set(doctor.specialization for doctor in doctors))
    
    # Get available today count using new slot system
    from doctors.models import DoctorTimeSlot
    available_today = DoctorTimeSlot.objects.filter(date=today, status='available').count()
    
    # Simplified statistics
    total_appointments = len(all_appointments)
    upcoming_count = len(upcoming_appointments)
    past_count = len(past_appointments)
    
    context = {
        'user': user,
        'patient': patient,
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments,
        'total_appointments': total_appointments,
        'upcoming_count': upcoming_count,
        'past_count': past_count,
        'doctors': doctors,
        'specializations': specializations,
        'available_today': available_today,
    }
    return render(request, 'patient/dashboard.html', context)

@login_required
def doctor_list(request):
    """List all available doctors"""
    doctors = Doctor.objects.filter(is_active=True)
    specialization_filter = request.GET.get('specialization')
    
    if specialization_filter:
        doctors = doctors.filter(specialization__icontains=specialization_filter)
    
    # Get unique specializations for filter
    specializations = Doctor.objects.filter(is_active=True).values_list('specialization', flat=True).distinct()
    
    context = {
        'doctors': doctors,
        'specializations': specializations,
        'specialization_filter': specialization_filter,
    }
    return render(request, 'patient/doctors/list.html', context)

@login_required
def doctor_detail(request, doctor_id):
    """View doctor details and available time slots using new slot system"""
    from doctors.models import Doctor
    from datetime import datetime, timedelta
    from .schedule_generator import ScheduleGeneratorService
    
    doctor = get_object_or_404(Doctor, id=doctor_id, is_active=True)
    schedule_service = ScheduleGeneratorService()
    
    # Generate available time slots for next 2 weeks
    available_slots = []
    start_date = timezone.now().date()
    
    for day_offset in range(14):  # Next 14 days
        current_date = start_date + timedelta(days=day_offset)
        
        # Skip past dates
        if current_date < start_date:
            continue
        
        # Get available slots for this date
        try:
            # Generate slots for this date if they don't exist
            schedule_service.generate_daily_slots(doctor, current_date)
            
            # Get available slots
            slots = ScheduleGeneratorService.get_available_slots_for_date(doctor, current_date)
            
            if slots:  # Only add days with available slots
                day_slots = []
                for slot in slots:
                    day_slots.append({
                        'time': slot.local_start_time,
                        'end_time': slot.local_end_time,
                        'date': current_date,
                        'slot_id': slot.id,
                        'booking_url': f"/patient/appointments/book/{doctor_id}/{current_date.strftime('%Y-%m-%d')}/{slot.local_start_time.strftime('%H:%M')}/"
                    })
                
                available_slots.append({
                    'date': current_date,
                    'day_name': current_date.strftime('%A'),
                    'day_name_short': current_date.strftime('%A')[:3],
                    'slots': day_slots
                })
        except ValueError:
            # No schedule template for this day
            continue
    
    context = {
        'doctor': doctor,
        'available_slots': available_slots,
        'today': timezone.now().date(),
    }
    return render(request, 'patient/doctors/doctor_profile_final.html', context)

@login_required
def book_appointment(request, doctor_id, date, start_time):
    """Book appointment using new slot system with database integrity"""
    from doctors.models import Doctor, DoctorTimeSlot
    from django.db import IntegrityError, transaction
    from django.utils import timezone
    from datetime import datetime, timedelta
    from .schedule_generator import ScheduleGeneratorService
    
    try:
        doctor = Doctor.objects.get(id=doctor_id, is_active=True)
    except Doctor.DoesNotExist:
        messages.error(request, 'Doctor not found.')
        return redirect('patient:doctors')
    
    # Parse and validate date and time
    try:
        appointment_date = datetime.strptime(date, '%Y-%m-%d').date()
        appointment_time = datetime.strptime(start_time, '%H:%M').time()
        end_time = (datetime.combine(datetime.today(), appointment_time) + timedelta(minutes=30)).time()
    except ValueError:
        messages.error(request, 'Invalid date or time format.')
        return redirect('patient:doctor_detail', doctor_id=doctor_id)
    
    # Validate appointment is not in the past
    today = timezone.now().date()
    if appointment_date < today:
        messages.error(request, 'Cannot book appointments in the past.')
        return redirect('patient:doctor_detail', doctor_id=doctor_id)
    
    # Validate appointment is within reasonable future (e.g., 3 months)
    max_future_date = today + timedelta(days=90)
    if appointment_date > max_future_date:
        messages.error(request, 'Cannot book appointments more than 3 months in advance.')
        return redirect('patient:doctor_detail', doctor_id=doctor_id)
    
    schedule_service = ScheduleGeneratorService()
    
    # Find the specific slot
    try:
        # Generate slots for this date if they don't exist
        schedule_service.generate_daily_slots(doctor, appointment_date)
        
        # Find the specific slot
        slot = DoctorTimeSlot.objects.get(
            doctor=doctor,
            date=appointment_date,
            start_datetime__time=appointment_time,
            status='available'
        )
    except DoctorTimeSlot.DoesNotExist:
        messages.error(request, 'This time slot is not available. Please choose another time.')
        return redirect('patient:doctor_detail', doctor_id=doctor_id)
    
    if request.method == 'POST':
        form = BookAppointmentForm(request.POST)
        if form.is_valid():
            # Use database transaction for atomic operation
            try:
                with transaction.atomic():
                    # Book the slot
                    if not ScheduleGeneratorService.book_slot(slot.id):
                        messages.error(request, 'This time slot is already booked. Please choose another time.')
                        return redirect('patient:doctor_detail', doctor_id=doctor_id)
                    
                    # Create the appointment
                    appointment = Appointment.objects.create(
                        patient=request.user,
                        doctor=doctor,
                        date=appointment_date,
                        start_time=appointment_time,
                        end_time=end_time,
                        symptoms=form.cleaned_data['symptoms'],
                        status='BOOKED'
                    )
                    
                    # Success - appointment booked
                    messages.success(request, f'Appointment booked successfully with Dr. {doctor.first_name} {doctor.last_name}!')
                    return redirect('accounts:patient_dashboard')
                    
            except IntegrityError:
                # Database constraint violation - slot already booked
                messages.error(request, 'This time slot is already booked. Please choose another time.')
                return redirect('patient:doctor_detail', doctor_id=doctor_id)
            except Exception as e:
                # Handle other unexpected errors
                messages.error(request, 'An error occurred while booking. Please try again.')
                return redirect('patient:doctor_detail', doctor_id=doctor_id)
        else:
            # Form validation failed
            context = {
                'doctor': doctor,
                'date': appointment_date,
                'start_time': appointment_time,
                'form': form,
            }
            return render(request, 'patient/appointments/book.html', context)
    
    # GET request - show booking form
    form = BookAppointmentForm()
    context = {
        'doctor': doctor,
        'date': appointment_date,
        'start_time': appointment_time,
        'end_time': end_time,
        'form': form,
    }
    return render(request, 'patient/appointments/book.html', context)

@login_required
def appointment_detail(request, appointment_id):
    """View appointment details"""
    try:
        appointment = Appointment.objects.get(id=appointment_id, patient=request.user)
    except Appointment.DoesNotExist:
        messages.error(request, 'Appointment not found.')
        return redirect('patient:dashboard')
    
    # Handle cancellation form submission
    if request.method == 'POST' and 'cancel_appointment' in request.POST:
        if appointment.status == 'BOOKED':
            appointment.status = 'CANCELLED'
            appointment.save()
            messages.success(request, 'Your appointment has been cancelled successfully.')
            return redirect('patient:appointment_detail', appointment_id=appointment_id)
        else:
            messages.error(request, 'This appointment cannot be cancelled.')
    
    context = {
        'appointment': appointment,
    }
    return render(request, 'patient/appointments/detail.html', context)

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm

@login_required
def change_password(request):
    """Handle password change for patients"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important to keep user logged in
            messages.success(request, 'Your password was successfully updated!')
            return redirect('patient:profile')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'patient/change_password.html', {'form': form})

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

@login_required
def patient_profile(request):
    """Patient profile page"""
    user = request.user
    
    # Get or create patient profile
    from doctors.models import Patient
    try:
        patient = Patient.objects.get(user=user)
    except Patient.DoesNotExist:
        patient = Patient.objects.create(
            user=user,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email
        )
    
    # Get appointment statistics
    total_appointments = Appointment.objects.filter(patient=user).count()
    upcoming_appointments = Appointment.objects.filter(
        patient=user, 
        date__gte=timezone.now().date(),
        status='BOOKED'
    ).count()
    
    # Get doctors the patient has appointments with
    my_doctors = Doctor.objects.filter(
        patient_appointments__patient=user
    ).distinct()
    
    context = {
        'user': user,
        'patient': patient,
        'total_appointments': total_appointments,
        'upcoming_appointments': upcoming_appointments,
        'my_doctors': my_doctors,
    }
    return render(request, 'patient/profile.html', context)

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
def cancel_appointment(request, appointment_id):
    """Cancel an appointment and free up the slot"""
    from doctors.models import DoctorTimeSlot
    from .schedule_generator import ScheduleGeneratorService
    
    appointment = get_object_or_404(
        Appointment, 
        id=appointment_id, 
        patient=request.user,
        status='BOOKED'
    )
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Mark appointment as cancelled
                appointment.status = 'CANCELLED'
                appointment.save()
                
                # Find and free up the slot
                try:
                    slot = DoctorTimeSlot.objects.get(
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
                
                messages.success(request, 'Appointment cancelled successfully!')
                return redirect('patient:past_appointments')
        except Exception as e:
            messages.error(request, 'An error occurred while cancelling. Please try again.')
    
    return render(request, 'patient/appointments/cancel.html', {'appointment': appointment})
