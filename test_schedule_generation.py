#!/usr/bin/env python
import os
import django
from datetime import date, time

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DoctorX.settings')
django.setup()

from doctors.models import Doctor, DoctorSchedule, DoctorTimeSlot
from appointments.schedule_generator import ScheduleGeneratorService

def debug_schedule_generation():
    print("🔍 DEBUG: Schedule Generation")
    print("=" * 50)
    
    # Get today's date
    today = date.today()
    print(f"📅 Today's date: {today}")
    print(f"📅 Today's weekday: {today.strftime('%A')}")
    
    # Check all doctors
    doctors = Doctor.objects.filter(is_active=True)
    print(f"\n👨‍⚕️ Active doctors: {doctors.count()}")
    
    for doctor in doctors:
        print(f"\n--- Dr. {doctor.first_name} {doctor.last_name} ---")
        
        # Check schedules for this doctor
        schedules = DoctorSchedule.objects.filter(doctor=doctor, is_active=True)
        print(f"Schedules: {schedules.count()}")
        
        for schedule in schedules:
            print(f"  📋 {schedule.day_of_week}: {schedule.start_time} - {schedule.end_time}")
        
        # Check slots for today
        today_slots = DoctorTimeSlot.objects.filter(
            doctor=doctor,
            date=today
        )
        print(f"📅 Today's slots: {today_slots.count()}")
        
        available_today = today_slots.filter(status='available').count()
        print(f"✅ Available today: {available_today}")
        
        # Try to generate slots for today
        generator = ScheduleGeneratorService()
        try:
            generated = generator.generate_daily_slots(doctor, today)
            print(f"🔧 Generated slots: {generated}")
        except Exception as e:
            print(f"❌ Error generating slots: {e}")
        
        # Check again after generation
        today_slots_after = DoctorTimeSlot.objects.filter(
            doctor=doctor,
            date=today
        )
        available_today_after = today_slots_after.filter(status='available').count()
        print(f"✅ Available after generation: {available_today_after}")
    
    # Check total available slots in system
    total_available = DoctorTimeSlot.objects.filter(
        date=today,
        status='available'
    ).count()
    print(f"\n🎯 Total available slots today: {total_available}")

if __name__ == '__main__':
    debug_schedule_generation()
