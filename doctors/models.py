from django.db import models
from django.contrib.auth.models import User
from django.core.validators import EmailValidator, RegexValidator
from django.utils import timezone
from datetime import datetime, timedelta

class Doctor(models.Model):
    """Doctor profile - passive entity, not a user"""
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
    ]
    
    # Personal Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES, blank=True, null=True)
        
    # Contact Information
    email = models.EmailField(validators=[EmailValidator()])
    phone = models.CharField(
        max_length=20, 
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number.')]
    )
    address = models.TextField(blank=True, null=True)
    
    # Professional Information
    specialization = models.CharField(max_length=200)
    qualification = models.CharField(max_length=200)
    experience_years = models.PositiveIntegerField(blank=True, null=True)
    license_number = models.CharField(max_length=50)
    department = models.CharField(max_length=200, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dr. {self.first_name} {self.last_name} - {self.specialization}"

    class Meta:
        verbose_name = 'Doctor'
        verbose_name_plural = 'Doctors'
        ordering = ['first_name', 'last_name']

class Availability(models.Model):
    """Doctor's weekly schedule"""
    DAY_CHOICES = [
        ('MONDAY', 'Monday'),
        ('TUESDAY', 'Tuesday'),
        ('WEDNESDAY', 'Wednesday'),
        ('THURSDAY', 'Thursday'),
        ('FRIDAY', 'Friday'),
        ('SATURDAY', 'Saturday'),
        ('SUNDAY', 'Sunday'),
    ]
    
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='availabilities')
    day_of_week = models.CharField(max_length=10, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['doctor', 'day_of_week']
        ordering = ['day_of_week', 'start_time']
        verbose_name = 'Availability'
        verbose_name_plural = 'Availabilities'
    
    def __str__(self):
        return f"{self.doctor.first_name} {self.doctor.last_name} - {self.get_day_of_week_display()}"

class DoctorTimeSlot(models.Model):
    """Generated 30-minute appointment slots in UTC"""
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('booked', 'Booked'),
        ('blocked', 'Blocked'),
    ]
    
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='time_slots')
    date = models.DateField()  # Local date for reference
    start_datetime = models.DateTimeField()  # UTC datetime
    end_datetime = models.DateTimeField()    # UTC datetime
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['doctor', 'date', 'start_datetime']
        ordering = ['date', 'start_datetime']
        verbose_name = 'Doctor Time Slot'
        verbose_name_plural = 'Doctor Time Slots'
    
    def __str__(self):
        local_start = self.start_datetime.astimezone(timezone.get_current_timezone())
        return f"{self.doctor.first_name} {self.last_name} - {self.date} {local_start.strftime('%H:%M')}"

    @property
    def is_available(self):
        return self.status == 'available' and self.date >= timezone.now().date()
    
    @property
    def local_start_time(self):
        """Get start time in local timezone"""
        return self.start_datetime.astimezone(timezone.get_current_timezone()).time()
    
    @property
    def local_end_time(self):
        """Get end time in local timezone"""
        return self.end_datetime.astimezone(timezone.get_current_timezone()).time()


class DoctorSchedule(models.Model):
    """Weekly schedule for doctors"""
    DAY_CHOICES = [
        ('MON', 'Monday'),
        ('TUE', 'Tuesday'),
        ('WED', 'Wednesday'),
        ('THU', 'Thursday'),
        ('FRI', 'Friday'),
        ('SAT', 'Saturday'),
        ('SUN', 'Sunday'),
    ]
    
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.CharField(max_length=3, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_start_time = models.TimeField(blank=True, null=True, help_text="Start time for break period")
    break_end_time = models.TimeField(blank=True, null=True, help_text="End time for break period")
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['doctor', 'day_of_week']
        ordering = ['day_of_week', 'start_time']
    
    def __str__(self):
        return f"{self.doctor.first_name} {self.doctor.last_name} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"
    
    

class Patient(models.Model):
    """Patient profile for healthcare system"""
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    medical_history = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['first_name', 'last_name']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_upcoming_appointments(self):
        """Get upcoming appointments for this patient"""
        from django.utils import timezone
        return self.appointments.filter(
            date__gte=timezone.now().date(),
            status='confirmed'
        ).order_by('date', 'start_time')
    
    def get_past_appointments(self):
        """Get past appointments for this patient"""
        from django.utils import timezone
        return self.appointments.filter(
            date__lt=timezone.now().date()
        ).order_by('-date', '-start_time')


class Appointment(models.Model):
    """Appointment model for patient bookings"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    symptoms = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date', 'start_time']
        unique_together = ['doctor', 'date', 'start_time']  # Prevent double booking for same doctor
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.doctor.full_name} - {self.date} {self.start_time}"
    
    @property
    def duration_minutes(self):
        """Calculate appointment duration in minutes"""
        if self.start_time and self.end_time:
            start = datetime.strptime(str(self.start_time), '%H:%M:%S')
            end = datetime.strptime(str(self.end_time), '%H:%M:%S')
            if end < start:  # Handle overnight
                end = end + timedelta(days=1)
            return int((end - start).total_seconds() / 60)
        return 0
    
    @property
    def is_upcoming(self):
        """Check if appointment is upcoming"""
        from django.utils import timezone
        now = timezone.now()
        appointment_datetime = timezone.make_aware(
            datetime.combine(self.date, self.start_time)
        )
        return appointment_datetime > now and self.status == 'confirmed'
    
    @property
    def is_past(self):
        """Check if appointment is in the past"""
        from django.utils import timezone
        now = timezone.now()
        appointment_datetime = timezone.make_aware(
            datetime.combine(self.date, self.start_time)
        )
        return appointment_datetime < now
    
    def can_be_cancelled(self):
        """Check if appointment can be cancelled"""
        from django.utils import timezone
        now = timezone.now()
        appointment_datetime = timezone.make_aware(
            datetime.combine(self.date, self.start_time)
        )
        # Can cancel if appointment is more than 2 hours away and not already cancelled/completed
        return (appointment_datetime - now).total_seconds() > 7200 and self.status in ['pending', 'confirmed']
    
    
