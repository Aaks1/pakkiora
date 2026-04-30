"""
Doctor Weekly Schedule Service
Handles proper schedule persistence and date generation
"""

from django.db import models
from doctors.models import Doctor


class DoctorWeeklySchedule(models.Model):
    """Doctor's weekly schedule - stores ONLY weekly availability"""
    WEEKDAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='weekly_schedules')
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField(default='09:00')
    end_time = models.TimeField(default='17:00')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['doctor', 'weekday']
        ordering = ['weekday', 'start_time']
        verbose_name = 'Doctor Weekly Schedule'
        verbose_name_plural = 'Doctor Weekly Schedules'
    
    def __str__(self):
        return f"{self.doctor.first_name} {self.doctor.last_name} - {self.get_weekday_display()}"


class WeeklyScheduleService:
    """Service for managing weekly schedules and generating dates dynamically"""
    
    def __init__(self):
        pass
    
    def get_doctor_weekly_schedules(self, doctor):
        """Get doctor's weekly schedules from the new model"""
        return DoctorWeeklySchedule.objects.filter(doctor=doctor, is_active=True)
    
    def setup_doctor_weekly_schedules(self, doctor):
        """Setup weekly schedules from old database fields to new model"""
        from django.db import connection
        
        # Get old schedule data
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT works_monday, works_tuesday, works_wednesday, works_thursday, 
                       works_friday, works_saturday, works_sunday, start_time, end_time
                FROM doctors_doctor 
                WHERE id = %s
            """, [doctor.id])
            result = cursor.fetchone()
            
            if result:
                # Clear existing weekly schedules
                DoctorWeeklySchedule.objects.filter(doctor=doctor).delete()
                
                # Create new weekly schedules
                weekday_fields = [
                    (0, bool(result[0])),  # Monday
                    (1, bool(result[1])),  # Tuesday
                    (2, bool(result[2])),  # Wednesday
                    (3, bool(result[3])),  # Thursday
                    (4, bool(result[4])),  # Friday
                    (5, bool(result[5])),  # Saturday
                    (6, bool(result[6])),  # Sunday
                ]
                
                schedules_created = []
                for weekday, works in weekday_fields:
                    if works:
                        schedule = DoctorWeeklySchedule(
                            doctor=doctor,
                            weekday=weekday,
                            start_time=result[7] or '09:00',
                            end_time=result[8] or '17:00',
                            is_active=True
                        )
                        schedules_created.append(schedule)
                
                # Bulk create
                if schedules_created:
                    DoctorWeeklySchedule.objects.bulk_create(schedules_created)
                
                return len(schedules_created)
        
        return 0
    
    def generate_schedule_for_next_3_weeks(self, doctor):
        """Generate schedule dates for next 21 days based on weekly schedules"""
        from datetime import date, timedelta, datetime
        
        # Get doctor's weekly schedules
        weekly_schedules = self.get_doctor_weekly_schedules(doctor)
        
        # Create weekday lookup
        weekday_schedules = {}
        for schedule in weekly_schedules:
            weekday_schedules[schedule.weekday] = schedule
        
        # Generate dates for next 21 days
        available_slots = []
        start_date = date.today()
        
        for day_offset in range(21):  # Next 21 days (3 weeks)
            current_date = start_date + timedelta(days=day_offset)
            weekday = current_date.weekday()
            
            # Check if doctor works on this weekday
            if weekday in weekday_schedules:
                weekly_schedule = weekday_schedules[weekday]
                
                # Generate 30-minute slots for this date
                slots = []
                start_time = weekly_schedule.start_time
                end_time = weekly_schedule.end_time
                
                current_time = datetime.combine(current_date, start_time)
                end_datetime = datetime.combine(current_date, end_time)
                
                while current_time + timedelta(minutes=30) <= end_datetime:
                    slot_end = current_time + timedelta(minutes=30)
                    
                    slots.append({
                        'time': current_time.time().strftime('%H:%M'),
                        'end_time': slot_end.time().strftime('%H:%M'),
                        'date': current_date,
                        'booking_url': f"/patient/appointments/book/{doctor.id}/{current_date.strftime('%Y-%m-%d')}/{current_time.time().strftime('%H:%M')}/"
                    })
                    
                    current_time = slot_end
                
                if slots:  # Only add days with slots
                    available_slots.append({
                        'date': current_date,
                        'day_name': current_date.strftime('%A'),
                        'day_name_short': current_date.strftime('%A')[:3],
                        'slots': slots,
                        'working_hours': f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}",
                        'total_slots': len(slots)
                    })
        
        return available_slots
    
    def clean_all_old_data(self):
        """Clean all old schedule and slot data"""
        from doctors.models import DoctorTimeSlot, Availability, DoctorSchedule
        
        print("Cleaning old schedule data...")
        
        # Delete old time slots
        slots_deleted = DoctorTimeSlot.objects.all().count()
        DoctorTimeSlot.objects.all().delete()
        print(f"Deleted {slots_deleted} time slots")
        
        # Delete old availabilities
        availabilities_deleted = Availability.objects.all().count()
        Availability.objects.all().delete()
        print(f"Deleted {availabilities_deleted} availabilities")
        
        # Delete old doctor schedules
        schedules_deleted = DoctorSchedule.objects.all().count()
        DoctorSchedule.objects.all().delete()
        print(f"Deleted {schedules_deleted} doctor schedules")
        
        print("Old data cleanup complete!")
        
        return {
            'slots_deleted': slots_deleted,
            'availabilities_deleted': availabilities_deleted,
            'schedules_deleted': schedules_deleted
        }
