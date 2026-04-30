#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DoctorX.settings')
django.setup()

from doctors.models import Doctor, DoctorSchedule
from datetime import time

def test_schedule_creation():
    print("Testing schedule creation...")
    
    # Get a doctor
    try:
        doctor = Doctor.objects.filter(is_active=True).first()
        if not doctor:
            print("No active doctors found!")
            return False
            
        print(f"Using doctor: {doctor.first_name} {doctor.last_name}")
        
        # Try to create a schedule
        try:
            # Check what days are already scheduled
            existing_days = DoctorSchedule.objects.filter(doctor=doctor).values_list('day_of_week', flat=True)
            available_days = [day for day in range(7) if day not in existing_days]
            
            if not available_days:
                print("All days already scheduled for this doctor!")
                return True
                
            day_to_use = available_days[0]
            schedule = DoctorSchedule.objects.create(
                doctor=doctor,
                day_of_week=day_to_use,  # Use an available day
                start_time=time(9, 0),
                end_time=time(17, 0),
                slot_duration=30,
                is_active=True
            )
            print(f"Created schedule: {schedule}")
            print(f"Day display: {schedule.get_day_of_week_display()}")
            return True
            
        except Exception as e:
            print(f"Error creating schedule: {e}")
            return False
            
    except Exception as e:
        print(f"Error getting doctor: {e}")
        return False

def test_schedule_form():
    print("\nTesting schedule form...")
    
    try:
        from doctors.forms import DoctorScheduleForm
        
        # Get a doctor
        doctor = Doctor.objects.filter(is_active=True).first()
        if not doctor:
            print("No active doctors found!")
            return False
        
        # Test form with valid data
        form_data = {
            'day_of_week': 1,  # Tuesday
            'start_time': '10:00',
            'end_time': '18:00',
            'slot_duration': 30,
            'is_active': True
        }
        
        form = DoctorScheduleForm(data=form_data, doctor=doctor)
        
        if form.is_valid():
            print("Form is valid!")
            print(f"Cleaned data: {form.cleaned_data}")
            return True
        else:
            print("Form errors:")
            for field, errors in form.errors.items():
                print(f"  {field}: {errors}")
            return False
            
    except Exception as e:
        print(f"Error testing form: {e}")
        return False

if __name__ == '__main__':
    success1 = test_schedule_creation()
    success2 = test_schedule_form()
    
    if success1 and success2:
        print("\nSchedule creation working correctly!")
    else:
        print("\nIssues found in schedule creation.")
