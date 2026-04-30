from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.generic import ListView, DetailView
from django.urls import reverse
from django.db import models
from doctors.models import Doctor, AppointmentSlot
from .models import Appointment
from .forms import AppointmentForm, BookAppointmentForm

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
    
    # Get available today count
    from doctors.models import AppointmentSlot
    available_today = AppointmentSlot.objects.filter(date=today, is_booked=False).count()
    
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
    """View doctor details and available time slots"""
    from doctors.models import Doctor
    from datetime import datetime, timedelta
    
    doctor = get_object_or_404(Doctor, id=doctor_id, is_active=True)
    
    # Generate available time slots for next 2 weeks
    available_slots = []
    start_date = timezone.now().date()
    
    for day_offset in range(14):  # Next 14 days
        current_date = start_date + timedelta(days=day_offset)
        
        # Skip weekends (optional - remove if you want weekends)
        if current_date.weekday() >= 5:  # Saturday (5) and Sunday (6)
            continue
        
        # Generate 30-minute slots from 9:00 AM to 5:00 PM
        day_slots = []
        for hour in range(9, 17):  # 9 AM to 5 PM
            for minute in [0, 30]:  # :00 and :30
                slot_time = datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
                
                # Check if slot is already booked (exclude cancelled appointments)
                is_booked = Appointment.objects.filter(
                    doctor=doctor,
                    date=current_date,
                    start_time=slot_time,
                    status__in=['BOOKED', 'COMPLETED', 'NO_SHOW']
                ).exists()
                
                if not is_booked:
                    # Calculate end time (30 minutes later)
                    end_time = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=slot_time.hour, minutes=slot_time.minute + 30)
                    end_time_only = end_time.time()
                    
                    day_slots.append({
                        'time': slot_time,
                        'end_time': end_time_only,
                        'date': current_date,
                        'booking_url': f"/patient/appointments/book/{doctor_id}/{current_date.strftime('%Y-%m-%d')}/{slot_time.strftime('%H:%M')}/"
                    })
        
        if day_slots:  # Only add days with available slots
            available_slots.append({
                'date': current_date,
                'day_name': current_date.strftime('%A'),
                'day_name_short': current_date.strftime('%A')[:3],  # Add short day name
                'slots': day_slots
            })
    
    context = {
        'doctor': doctor,
        'available_slots': available_slots,
        'today': timezone.now().date(),
    }
    return render(request, 'patient/doctors/doctor_profile_final.html', context)

@login_required
def book_appointment(request, doctor_id, date, start_time):
    """Robust appointment booking with database integrity and concurrency handling"""
    from doctors.models import Doctor
    from django.db import IntegrityError, transaction
    from django.utils import timezone
    from datetime import datetime, timedelta
    
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
    
    # Validate business hours (9 AM - 5 PM, weekdays only)
    if appointment_date.weekday() >= 5:  # Weekend (5=Saturday, 6=Sunday)
        messages.error(request, 'Appointments are only available on weekdays.')
        return redirect('patient:doctor_detail', doctor_id=doctor_id)
    
    if appointment_time < datetime.strptime('09:00', '%H:%M').time() or \
       appointment_time > datetime.strptime('16:30', '%H:%M').time():
        messages.error(request, 'Appointments are only available between 9:00 AM and 4:30 PM.')
        return redirect('patient:doctor_detail', doctor_id=doctor_id)
    
    if request.method == 'POST':
        form = BookAppointmentForm(request.POST)
        if form.is_valid():
            # Use database transaction for atomic operation
            try:
                with transaction.atomic():
                    # Quick conflict check with single query
                    conflicts = Appointment.objects.select_for_update().filter(
                        date=appointment_date,
                        start_time=appointment_time,
                        status='BOOKED'
                    ).filter(
                        models.Q(doctor=doctor) | models.Q(patient=request.user)
                    ).first()
                    
                    if conflicts:
                        if conflicts.doctor == doctor:
                            messages.error(request, 'This time slot is already booked. Please choose another time.')
                        else:
                            messages.error(request, 'You already have an appointment at this time.')
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
    """Cancel an appointment"""
    appointment = get_object_or_404(
        Appointment, 
        id=appointment_id, 
        patient=request.user,
        status='BOOKED'
    )
    
    if request.method == 'POST':
        # Mark appointment as cancelled
        appointment.status = 'CANCELLED'
        appointment.save()
        
        # Free up the slot
        appointment.slot.is_booked = False
        appointment.slot.save()
        
        messages.success(request, 'Appointment cancelled successfully!')
        return redirect('patient:appointments')
    
    return render(request, 'patient/appointments/cancel.html', {'appointment': appointment})
