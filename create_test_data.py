#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DoctorX.settings')
django.setup()

from doctors.models import Doctor, DoctorSchedule, Patient
from django.contrib.auth.models import User
from datetime import time

def create_test_data():
    print("Creating test data for new architecture...")
    
    # Create test doctors
    doctors_data = [
        {
            'first_name': 'John',
            'last_name': 'Smith',
            'specialization': 'Cardiology',
            'email': 'john.smith@hospital.com',
            'phone': '+1234567890',
            'license_number': 'MD123456',
            'qualification': 'MD Cardiology',
            'experience_years': 10,
        },
        {
            'first_name': 'Sarah',
            'last_name': 'Johnson',
            'specialization': 'Neurology',
            'email': 'sarah.johnson@hospital.com',
            'phone': '+1234567891',
            'license_number': 'MD789012',
            'qualification': 'MD Neurology',
            'experience_years': 8,
        },
        {
            'first_name': 'Michael',
            'last_name': 'Brown',
            'specialization': 'Pediatrics',
            'email': 'michael.brown@hospital.com',
            'phone': '+1234567892',
            'license_number': 'MD345678',
            'qualification': 'MD Pediatrics',
            'experience_years': 12,
        },
    ]
    
    created_doctors = []
    for doctor_data in doctors_data:
        doctor, created = Doctor.objects.get_or_create(
            email=doctor_data['email'],
            defaults=doctor_data
        )
        if created:
            created_doctors.append(doctor)
            print(f"Created Dr. {doctor.first_name} {doctor.last_name}")
        else:
            created_doctors.append(doctor)
            print(f"Dr. {doctor.first_name} {doctor.last_name} already exists")
    
    # Create schedules for each doctor
    for doctor in created_doctors:
        schedules_data = [
            {
                'day_of_week': 0,  # Monday
                'start_time': time(9, 0),
                'end_time': time(17, 0),
                'slot_duration': 30,
            },
            {
                'day_of_week': 1,  # Tuesday
                'start_time': time(9, 0),
                'end_time': time(17, 0),
                'slot_duration': 30,
            },
            {
                'day_of_week': 2,  # Wednesday
                'start_time': time(9, 0),
                'end_time': time(14, 0),
                'slot_duration': 30,
            },
            {
                'day_of_week': 3,  # Thursday
                'start_time': time(9, 0),
                'end_time': time(17, 0),
                'slot_duration': 30,
            },
            {
                'day_of_week': 4,  # Friday
                'start_time': time(9, 0),
                'end_time': time(17, 0),
                'slot_duration': 30,
            },
        ]
        
        for schedule_data in schedules_data:
            schedule, created = DoctorSchedule.objects.get_or_create(
                doctor=doctor,
                day_of_week=schedule_data['day_of_week'],
                defaults=schedule_data
            )
            if created:
                day_name = dict(DoctorSchedule.DAYS).get(schedule_data['day_of_week'], 'Unknown')
                print(f"  Created {day_name} schedule for Dr. {doctor.first_name} {doctor.last_name}")
            else:
                day_name = dict(DoctorSchedule.DAYS).get(schedule_data['day_of_week'], 'Unknown')
                print(f"  {day_name} schedule already exists for Dr. {doctor.first_name} {doctor.last_name}")
    
    # Create test patient user
    patient_user, created = User.objects.get_or_create(
        username='testpatient',
        defaults={
            'email': 'patient@test.com',
            'first_name': 'Test',
            'last_name': 'Patient',
            'is_staff': False,
        }
    )
    
    if created:
        patient_user.set_password('testpass123')
        patient_user.save()
        
        # Create patient profile
        patient, _ = Patient.objects.get_or_create(
            user=patient_user,
            defaults={
                'first_name': 'Test',
                'last_name': 'Patient',
                'phone': '+1234567899',
                'address': '123 Test Street, Test City',
            }
        )
        print(f"Created test patient user: {patient_user.username}")
    else:
        print(f"Test patient user already exists: {patient_user.username}")
    
    print("\nTest data creation complete!")
    print("\nSummary:")
    print(f"Doctors: {Doctor.objects.count()}")
    print(f"Schedules: {DoctorSchedule.objects.count()}")
    print(f"Patients: {Patient.objects.count()}")
    
    print("\nTest Login:")
    print("Username: testpatient")
    print("Password: testpass123")
    
    print("\nTest the new patient flow:")
    print("1. Login as test patient")
    print("2. Select a date")
    print("3. View available doctors")
    print("4. Click on a doctor to see slots")
    print("5. Book an appointment")

if __name__ == '__main__':
    create_test_data()
