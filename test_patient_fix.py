#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DoctorX.settings')
django.setup()

from doctors.models import Patient, Appointment
from django.contrib.auth.models import User

def test_patient_fix():
    print("Testing Patient model fix...")
    
    # Get test patient user
    try:
        user = User.objects.get(username='testpatient')
        print(f"Found test user: {user.username}")
    except User.DoesNotExist:
        print("Test user not found - creating...")
        user = User.objects.create_user(
            username='testpatient',
            email='patient@test.com',
            first_name='Test',
            last_name='Patient',
            password='testpass123'
        )
        print(f"Created test user: {user.username}")
    
    # Test Patient creation
    try:
        patient, created = Patient.objects.get_or_create(
            user=user,
            defaults={
                "first_name": user.first_name or "Unknown",
                "last_name": user.last_name or "User",
            }
        )
        if created:
            print(f"Created patient: {patient.first_name} {patient.last_name}")
        else:
            print(f"Patient already exists: {patient.first_name} {patient.last_name}")
        
        # Test Appointment query
        appointments = Appointment.objects.filter(patient=patient)
        print(f"Found {appointments.count()} appointments for patient")
        
        print("Patient model fix working correctly!")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == '__main__':
    test_patient_fix()
