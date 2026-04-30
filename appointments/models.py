from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import date

class Appointment(models.Model):
    """Simple appointment model with database integrity"""
    STATUS_CHOICES = [
        ('BOOKED', 'Booked'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
        ('NO_SHOW', 'No Show'),
    ]
    
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments', null=True, blank=True)
    doctor = models.ForeignKey('doctors.Doctor', on_delete=models.CASCADE, related_name='patient_appointments', null=True, blank=True)
    date = models.DateField(default=date.today)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='BOOKED')
    symptoms = models.TextField(blank=True, help_text="Patient symptoms/reason for visit")
    notes = models.TextField(blank=True, help_text="Doctor notes after consultation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Appointment: {self.patient.username} with Dr. {self.doctor.first_name} on {self.date} at {self.start_time}"

    def clean(self):
        if not self.patient_id or not self.doctor_id:
            raise ValidationError("Patient and doctor are required.")
        if not self.start_time or not self.end_time:
            raise ValidationError("Start and end times are required.")
        if self.end_time <= self.start_time:
            raise ValidationError("End time must be later than start time.")

    class Meta:
        verbose_name = 'Appointment'
        verbose_name_plural = 'Appointments'
        ordering = ['date', 'start_time']
        # CRITICAL: Database enforces uniqueness - prevents double booking
        unique_together = [
            ('doctor', 'date', 'start_time'),  # One doctor = one time slot = one patient
        ]

    @property
    def appointment_date(self):
        return self.date

    @property
    def appointment_time(self):
        return self.start_time
