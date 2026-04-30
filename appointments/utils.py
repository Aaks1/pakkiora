from datetime import datetime, timedelta, date
from doctors.models import Doctor, DoctorSchedule, Appointment


def get_available_doctors(date):
    """Get doctors who have schedules for a specific date"""
    weekday = date.weekday()

    schedules = DoctorSchedule.objects.filter(
        day_of_week=weekday,
        is_active=True
    ).select_related("doctor")

    return schedules


def generate_slots(schedule, date):
    """Generate time slots for a doctor on a specific date"""
    start = datetime.combine(date, schedule.start_time)
    end = datetime.combine(date, schedule.end_time)
    duration = timedelta(minutes=schedule.slot_duration)

    slots = []

    while start + duration <= end:
        slots.append({
            "start_time": start.time(),
            "end_time": (start + duration).time()
        })
        start += duration

    return slots


def get_available_slots(doctor, date):
    """Get available slots for a doctor on a specific date"""
    weekday = date.weekday()

    try:
        schedule = DoctorSchedule.objects.get(
            doctor=doctor,
            day_of_week=weekday,
            is_active=True
        )
    except DoctorSchedule.DoesNotExist:
        return []

    # Generate all possible slots
    all_slots = generate_slots(schedule, date)

    # Get already booked slots
    booked = Appointment.objects.filter(
        doctor=doctor,
        date=date
    ).values_list("start_time", flat=True)

    # Filter out booked slots
    available_slots = [
        slot for slot in all_slots if slot["start_time"] not in booked
    ]

    return available_slots


def book_appointment(patient, doctor, date, start_time, end_time):
    """Book an appointment safely with atomic transaction"""
    from django.db import transaction
    
    with transaction.atomic():
        # Check if slot is already booked
        existing = Appointment.objects.filter(
            doctor=doctor,
            date=date,
            start_time=start_time
        ).exists()
        
        if existing:
            return False, "Slot already booked"
        
        # Create the appointment
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            date=date,
            start_time=start_time,
            end_time=end_time,
            status='confirmed'
        )
        
        return True, appointment
