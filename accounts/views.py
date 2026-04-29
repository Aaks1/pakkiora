from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from .models import UserProfile, AdminProfile
from doctors.models import Doctor, DoctorSchedule, Patient
from appointments.models import Appointment
from .forms import UserRegistrationForm, AdminUserForm
from doctors.forms import DoctorForm, DoctorScheduleForm

def safe_message(request, level, message):
    """Safe message handling for serverless environments"""
    try:
        if level == 'success':
            messages.success(request, message)
        elif level == 'error':
            messages.error(request, message)
        elif level == 'warning':
            messages.warning(request, message)
        elif level == 'info':
            messages.info(request, message)
    except Exception:
        # Silently fail if messages middleware is not available
        pass

def home(request):
    """Render to landing page"""
    return render(request, 'index.html')

from django.views.decorators.csrf import csrf_protect

@csrf_protect
def login_view(request):
    """Handle user login"""
    # Clear any existing messages to prevent Django default messages
    try:
        storage = messages.get_messages(request)
        storage.used = True
    except Exception:
        pass  # Messages middleware not available
    
    if request.method == 'POST':
        from django.contrib.auth import authenticate
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            
            # Check if user has a patient profile (for regular users)
            try:
                patient = Patient.objects.get(user=user)
                safe_message(request, 'success', f'Welcome back, {patient.first_name}!')
                return redirect('accounts:patient_dashboard')
            except Patient.DoesNotExist:
                # If no patient profile, check if it's an admin/staff user
                if user.is_staff:
                    return redirect('admin_dashboard')
                else:
                    # Regular user without patient profile - create one or redirect to register
                    safe_message(request, 'error', 'No patient profile found. Please complete your registration.')
                    return redirect('accounts:register')
            except Exception as e:
                safe_message(request, 'error', f'Login error: {str(e)}')
        else:
            safe_message(request, 'error', 'Invalid username or password.')
    
    return render(request, 'login.html')

def register_view(request):
    """Handle user registration"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                
                # Create patient profile
                patient = Patient.objects.create(
                    user=user,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    phone=form.cleaned_data.get('phone', ''),
                    address=form.cleaned_data.get('address', ''),
                    date_of_birth=form.cleaned_data.get('date_of_birth'),
                    blood_group=form.cleaned_data.get('blood_group', ''),
                    allergies=form.cleaned_data.get('allergies', ''),
                    medical_history=form.cleaned_data.get('medical_conditions', '')
                )
                
                safe_message(request, 'success', 'Registration successful! Please login.')
                return redirect('accounts:login')
                
            except Exception as e:
                # Delete the user if patient creation fails
                if 'user' in locals():
                    user.delete()
                safe_message(request, 'error', f'Error creating patient profile: {str(e)}')
                return render(request, 'register.html', {'form': form})
    else:
        form = UserRegistrationForm()
    
    return render(request, 'register.html', {'form': form})

@login_required
def profile_view(request):
    """View and edit user profile"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        # Update user info
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')
        request.user.save()
        
        # Update profile info
        profile.phone = request.POST.get('phone', '')
        profile.date_of_birth = request.POST.get('date_of_birth') or None
        profile.address = request.POST.get('address', '')
        profile.city = request.POST.get('city', '')
        profile.state = request.POST.get('state', '')
        profile.postal_code = request.POST.get('postal_code', '')
        profile.country = request.POST.get('country', '')
        profile.allergies = request.POST.get('allergies', '')
        profile.medical_conditions = request.POST.get('medical_conditions', '')
        profile.save()
        
        safe_message(request, 'success', 'Profile updated successfully!')
        return redirect('accounts:profile')
    
    return render(request, 'profile.html', {'profile': profile})

@csrf_protect
def logout_view(request):
    """Handle user logout"""
    if request.method == 'POST':
        logout(request)
        safe_message(request, 'success', 'You have been logged out successfully.')
    return redirect('accounts:login')

@login_required
def patient_dashboard(request):
    """Patient dashboard view with comprehensive information"""
    from datetime import date
    from django.utils import timezone
    from appointments.models import Appointment
    
    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        safe_message(request, 'error', 'Patient profile not found. Please register as a patient.')
        return redirect('accounts:login')
    
    # Get available doctors
    doctors = Doctor.objects.filter(is_active=True)
    
    # Get patient's upcoming appointments
    upcoming_appointments = Appointment.objects.filter(
        patient=request.user, 
        date__gte=timezone.now().date(),
        status='BOOKED'
    ).select_related('doctor').order_by('date', 'start_time')
    
    # Calculate available slots today
    available_today = 0
    for doctor in doctors:
        from doctors.models import Appointment as DoctorAppointment
        slots = DoctorAppointment.get_available_slots(doctor, date.today())
        available_today += len(slots)
    
    # Get specializations for filtering
    specializations = list(doctors.values_list('specialization', flat=True).distinct())
    
    context = {
        'patient': patient,
        'doctors': doctors,
        'upcoming_appointments': upcoming_appointments,
        'available_today': available_today,
        'specializations': specializations
    }
    
    return render(request, 'patient/dashboard.html', context)

# Admin Views
def check_is_admin(user):
    """Check if user is admin (staff)"""
    return user.is_staff

@login_required
@user_passes_test(check_is_admin)
def admin_dashboard(request):
    """Main admin dashboard"""
    context = {
        'total_users': User.objects.filter(is_staff=False).count(),
        'total_doctors': Doctor.objects.count(),
        'total_admins': User.objects.filter(is_staff=True).count(),
        'active_doctors': Doctor.objects.filter(is_active=True).count(),
        'recent_users': User.objects.filter(is_staff=False).order_by('-date_joined')[:5],
        'recent_doctors': Doctor.objects.order_by('-created_at')[:5],
        'user': request.user,
    }
    return render(request, 'admin/dashboard.html', context)

@login_required
@user_passes_test(check_is_admin)
def admin_list(request):
    """List all admin users"""
    admins = User.objects.filter(is_staff=True).order_by('-date_joined')
    
    # Apply search filter
    search_query = request.GET.get('search')
    if search_query:
        admins = admins.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    return render(request, 'admin/admin_list.html', {'admins': admins, 'user': request.user})

@login_required
@user_passes_test(check_is_admin)
def admin_create(request):
    """Create new admin user"""
    if request.method == 'POST':
        form = AdminUserForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.is_staff = True
                user.is_superuser = False  # Regular admin, not superuser
                user.save()
                
                # Create admin profile
                AdminProfile.objects.create(
                    user=user,
                    phone=form.cleaned_data.get('phone', ''),
                    department=form.cleaned_data.get('department', '')
                )
                
                safe_message(request, 'success', f'Admin {user.username} created successfully!')
                return redirect('admin_dashboard')
            except Exception as e:
                safe_message(request, 'error', f'Error creating admin: {str(e)}')
        else:
            # Form is not valid, show errors
            for field, errors in form.errors.items():
                for error in errors:
                    safe_message(request, 'error', f'{field}: {error}')
    else:
        form = AdminUserForm()
    
    return render(request, 'admin/admin_create.html', {'form': form, 'user': request.user})

@login_required
@user_passes_test(check_is_admin)
def admin_edit(request, admin_id):
    """Edit admin user"""
    admin = get_object_or_404(User, id=admin_id, is_staff=True)
    
    if request.method == 'POST':
        form = AdminUserForm(request.POST, instance=admin)
        if form.is_valid():
            form.save()
            
            # Update admin profile
            try:
                profile = admin.admin_profile
                profile.phone = form.cleaned_data.get('phone', profile.phone)
                profile.department = form.cleaned_data.get('department', profile.department)
                profile.save()
            except AdminProfile.DoesNotExist:
                AdminProfile.objects.create(
                    user=admin,
                    phone=form.cleaned_data.get('phone', ''),
                    department=form.cleaned_data.get('department', '')
                )
            
            safe_message(request, 'success', f'Admin {admin.username} updated successfully!')
            return redirect('admin_list')
    else:
        form = AdminUserForm(instance=admin)
        # Pre-fill profile data
        try:
            profile = admin.admin_profile
            form.fields['phone'].initial = profile.phone
            form.fields['department'].initial = profile.department
        except AdminProfile.DoesNotExist:
            pass
    
    return render(request, 'admin/admin_edit.html', {'form': form, 'admin': admin, 'user': request.user})

@login_required
@user_passes_test(check_is_admin)
def admin_delete(request, admin_id):
    """Delete admin user"""
    admin = get_object_or_404(User, id=admin_id, is_staff=True)
    
    if request.method == 'POST':
        confirm_username = request.POST.get('confirm_username')
        confirm_delete = request.POST.get('confirm_delete')
        
        # Validation checks
        if not confirm_delete:
            safe_message(request, 'error', 'You must confirm the deletion.')
            return render(request, 'admin/admin_delete.html', {'admin': admin, 'user': request.user})
        
        if confirm_username != admin.username:
            safe_message(request, 'error', 'Username confirmation does not match.')
            return render(request, 'admin/admin_delete.html', {'admin': admin, 'user': request.user})
        
        # Prevent self-deletion
        if admin.id == request.user.id:
            safe_message(request, 'error', 'You cannot delete your own account.')
            return render(request, 'admin/admin_delete.html', {'admin': admin, 'user': request.user})
        
        username = admin.username
        admin.delete()
        safe_message(request, 'success', f'Admin {username} deleted successfully!')
        return redirect('admin_list')
    
    return render(request, 'admin/admin_delete.html', {'admin': admin, 'user': request.user})

@login_required
@user_passes_test(check_is_admin)
def doctor_list(request):
    """List all doctors"""
    doctors = Doctor.objects.all().order_by('-created_at')
    
    # Apply search filter
    search_query = request.GET.get('search')
    if search_query:
        doctors = doctors.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(specialization__icontains=search_query) |
            Q(department__icontains=search_query)
        )
    
    return render(request, 'admin/doctor_list.html', {'doctors': doctors, 'user': request.user})

@login_required
@user_passes_test(check_is_admin)
def doctor_create(request):
    """Create new doctor"""
    if request.method == 'POST':
        form = DoctorForm(request.POST, request.FILES)
        if form.is_valid():
            # Create doctor profile without user account
            doctor = form.save()
            
            safe_message(request, 'success', f'Dr. {doctor.first_name} {doctor.last_name} created successfully!')
            return redirect('admin_dashboard')
        else:
            # Form is not valid, show errors
            for field, errors in form.errors.items():
                for error in errors:
                    safe_message(request, 'error', f'{field}: {error}')
    else:
        form = DoctorForm()
    
    return render(request, 'admin/doctor_create.html', {'form': form, 'user': request.user})

@login_required
@user_passes_test(check_is_admin)
def doctor_edit(request, doctor_id):
    """Edit doctor"""
    doctor = get_object_or_404(Doctor, id=doctor_id)
    
    if request.method == 'POST':
        form = DoctorForm(request.POST, instance=doctor)
        if form.is_valid():
            form.save()
            safe_message(request, 'success', f'Dr. {doctor.first_name} {doctor.last_name} updated successfully!')
            return redirect('doctor_list')
    else:
        form = DoctorForm(instance=doctor)
    
    return render(request, 'admin/doctor_edit.html', {'form': form, 'doctor': doctor, 'user': request.user})

@login_required
@user_passes_test(check_is_admin)
def doctor_delete(request, doctor_id):
    """Delete doctor"""
    doctor = get_object_or_404(Doctor, id=doctor_id)
    
    if request.method == 'POST':
        doctor_name = f"Dr. {doctor.first_name} {doctor.last_name}"
        doctor.delete()
        safe_message(request, 'success', f'{doctor_name} deleted successfully!')
        return redirect('doctor_list')
    
    return render(request, 'admin/doctor_delete.html', {'doctor': doctor, 'user': request.user})

@login_required
@user_passes_test(check_is_admin)
def doctor_toggle_active(request, doctor_id):
    """Toggle doctor active status"""
    doctor = get_object_or_404(Doctor, id=doctor_id)
    doctor.is_active = not doctor.is_active
    doctor.save()
    
    status = "activated" if doctor.is_active else "deactivated"
    safe_message(request, 'success', f'Dr. {doctor.first_name} {doctor.last_name} {status} successfully!')
    return redirect('doctor_list')


@login_required
@user_passes_test(check_is_admin)
def doctor_schedule_list(request, doctor_id):
    """List all schedules for a specific doctor"""
    doctor = get_object_or_404(Doctor, id=doctor_id)
    schedules = doctor.schedules.all().order_by('day_of_week', 'start_time')
    
    return render(request, 'admin/doctor_schedule_list.html', {
        'doctor': doctor,
        'schedules': schedules
    })


@login_required
@user_passes_test(check_is_admin)
def doctor_schedule_create(request, doctor_id):
    """Create a new schedule for a doctor"""
    doctor = get_object_or_404(Doctor, id=doctor_id)
    
    if request.method == 'POST':
        form = DoctorScheduleForm(request.POST, doctor=doctor)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.doctor = doctor
            schedule.save()
            safe_message(request, 'success', f'Schedule created for Dr. {doctor.first_name} {doctor.last_name}!')
            return redirect('doctor_schedule_list', doctor_id=doctor_id)
    else:
        form = DoctorScheduleForm(doctor=doctor)
    
    return render(request, 'admin/doctor_schedule_form.html', {
        'form': form,
        'doctor': doctor,
        'action': 'Create'
    })


@login_required
@user_passes_test(check_is_admin)
def doctor_schedule_edit(request, doctor_id, schedule_id):
    """Edit an existing doctor schedule"""
    doctor = get_object_or_404(Doctor, id=doctor_id)
    schedule = get_object_or_404(DoctorSchedule, id=schedule_id, doctor=doctor)
    
    if request.method == 'POST':
        form = DoctorScheduleForm(request.POST, instance=schedule, doctor=doctor)
        if form.is_valid():
            form.save()
            safe_message(request, 'success', f'Schedule updated for Dr. {doctor.first_name} {doctor.last_name}!')
            return redirect('doctor_schedule_list', doctor_id=doctor_id)
    else:
        form = DoctorScheduleForm(instance=schedule, doctor=doctor)
    
    return render(request, 'admin/doctor_schedule_form.html', {
        'form': form,
        'doctor': doctor,
        'schedule': schedule,
        'action': 'Edit'
    })


@login_required
@user_passes_test(check_is_admin)
def doctor_schedule_delete(request, doctor_id, schedule_id):
    """Delete a doctor schedule"""
    doctor = get_object_or_404(Doctor, id=doctor_id)
    schedule = get_object_or_404(DoctorSchedule, id=schedule_id, doctor=doctor)
    
    if request.method == 'POST':
        schedule.delete()
        safe_message(request, 'success', f'Schedule deleted for Dr. {doctor.first_name} {doctor.last_name}!')
        return redirect('doctor_schedule_list', doctor_id=doctor_id)
    
    return render(request, 'admin/doctor_schedule_delete.html', {
        'doctor': doctor,
        'schedule': schedule
    })


@login_required
@user_passes_test(check_is_admin)
def doctor_schedule_toggle(request, doctor_id, schedule_id):
    """Toggle schedule active status"""
    doctor = get_object_or_404(Doctor, id=doctor_id)
    schedule = get_object_or_404(DoctorSchedule, id=schedule_id, doctor=doctor)
    
    schedule.is_active = not schedule.is_active
    schedule.save()
    
    status = "activated" if schedule.is_active else "deactivated"
    safe_message(request, 'success', f'Schedule {status} for Dr. {doctor.first_name} {doctor.last_name}!')
    return redirect('doctor_schedule_list', doctor_id=doctor_id)


# Appointment Management Views
@login_required
@user_passes_test(check_is_admin)
def appointment_management(request):
    """Admin appointment management - view all appointments"""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    doctor_filter = request.GET.get('doctor', '')
    
    appointments = Appointment.objects.all().select_related('patient', 'doctor').order_by('-date', '-start_time')
    
    if search_query:
        appointments = appointments.filter(
            Q(patient__username__icontains=search_query) |
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query) |
            Q(doctor__first_name__icontains=search_query) |
            Q(doctor__last_name__icontains=search_query)
        )
    
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    
    if doctor_filter:
        appointments = appointments.filter(doctor_id=doctor_filter)
    
    # Get filters for dropdowns
    doctors = Doctor.objects.filter(is_active=True)
    status_choices = Appointment.STATUS_CHOICES
    
    context = {
        'appointments': appointments,
        'doctors': doctors,
        'status_choices': status_choices,
        'search_query': search_query,
        'status_filter': status_filter,
        'doctor_filter': doctor_filter,
    }
    return render(request, 'admin/appointments/appointment_list.html', context)


@login_required
@user_passes_test(check_is_admin)
def appointment_detail_admin(request, appointment_id):
    """Admin view appointment details"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    context = {
        'appointment': appointment,
    }
    return render(request, 'admin/appointments/appointment_detail.html', context)


@login_required
@user_passes_test(check_is_admin)
def cancel_appointment_admin(request, appointment_id):
    """Admin cancel appointment"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    if request.method == 'POST':
        appointment.status = 'CANCELLED'
        appointment.save()
        safe_message(request, 'success', f'Appointment for {appointment.patient.username} with Dr. {appointment.doctor.first_name} has been cancelled.')
        return redirect('admin_appointment_management')
    
    context = {
        'appointment': appointment,
    }
    return render(request, 'admin/appointments/appointment_cancel.html', context)


@login_required
@user_passes_test(check_is_admin)
def doctor_appointments(request, doctor_id):
    """View appointments for a specific doctor"""
    doctor = get_object_or_404(Doctor, id=doctor_id)
    appointments = Appointment.objects.filter(doctor=doctor).select_related('patient').order_by('-date', '-start_time')
    
    context = {
        'doctor': doctor,
        'appointments': appointments,
    }
    return render(request, 'admin/appointments/doctor_appointments.html', context)


# User Management Views
@login_required
@user_passes_test(check_is_admin)
def user_management(request):
    """Admin user management - view all users"""
    search_query = request.GET.get('search', '')
    user_type = request.GET.get('user_type', '')
    
    users = User.objects.all().order_by('-date_joined')
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if user_type:
        if user_type == 'patient':
            users = users.filter(patient_profile__isnull=False)
        elif user_type == 'admin':
            users = users.filter(is_staff=True)
        elif user_type == 'regular':
            users = users.filter(is_staff=False, patient_profile__isnull=True)
    
    # Add user profile information
    user_data = []
    for user in users:
        user_info = {
            'user': user,
            'is_patient': hasattr(user, 'patient_profile'),
            'is_admin': user.is_staff,
            'appointment_count': Appointment.objects.filter(patient=user).count() if hasattr(user, 'patient_profile') else 0,
        }
        user_data.append(user_info)
    
    context = {
        'users': user_data,
        'search_query': search_query,
        'user_type': user_type,
    }
    return render(request, 'admin/users/user_list.html', context)


@login_required
@user_passes_test(check_is_admin)
def user_detail_admin(request, user_id):
    """Admin view user details and appointments"""
    user = get_object_or_404(User, id=user_id)
    
    # Get user profile information
    is_patient = hasattr(user, 'patient_profile')
    is_admin = user.is_staff
    
    # Get appointments if user is a patient
    appointments = []
    if is_patient:
        appointments = Appointment.objects.filter(patient=user).select_related('doctor').order_by('-date', '-start_time')
    
    context = {
        'user': user,
        'is_patient': is_patient,
        'is_admin': is_admin,
        'appointments': appointments,
    }
    return render(request, 'admin/users/user_detail.html', context)





