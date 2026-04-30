from datetime import datetime, timedelta, date
from django.db import transaction
from django.utils import timezone
from typing import List


class ScheduleGeneratorService:
    """
    Service for generating 30-minute appointment slots based on doctor schedules.
    
    This service implements the core business logic for slot generation:
    - Fixed 30-minute slot duration
    - UTC datetime storage
    - Break time handling
    - Bulk operations for performance
    - Idempotent slot generation
    """
    
    SLOT_DURATION_MINUTES = 30
    
        
    def generate_daily_slots(self, doctor, target_date: date) -> int:
        """
        Generate 30-minute slots for a doctor on a specific date.
        
        Args:
            doctor: Doctor instance
            target_date: Date for which to generate slots
            
        Returns:
            int: Number of slots generated
            
        Raises:
            ValueError: If no schedule template exists for the weekday
        """
        from doctors.models import DoctorSchedule, DoctorTimeSlot
        
        # Get weekday mapping (0=Monday, 6=Sunday)
        weekday = target_date.weekday()
        weekday_mapping = {
            0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI', 5: 'SAT', 6: 'SUN'
        }
        
        # Get schedule template for this weekday
        try:
            schedule = DoctorSchedule.objects.get(
                doctor=doctor,
                day_of_week=weekday_mapping[weekday],
                is_active=True
            )
        except DoctorSchedule.DoesNotExist:
            raise ValueError(f"No schedule template found for doctor {doctor} on weekday {weekday_mapping[weekday]}")
        
        # Delete existing slots for this date (idempotent)
        DoctorTimeSlot.objects.filter(doctor=doctor, date=target_date).delete()
        
        # Generate slots
        slots = self._generate_slots_for_schedule(schedule, doctor, target_date)
        
        # Bulk create slots
        if slots:
            DoctorTimeSlot.objects.bulk_create(slots, batch_size=500)
        
        return len(slots)
    
    def _generate_slots_for_schedule(self, schedule, doctor, target_date: date) -> List:
        """
        Generate slot objects for a single day's schedule.
        
        Args:
            schedule: DoctorSchedule instance
            doctor: Doctor instance
            target_date: Date for slot generation
            
        Returns:
            List: List of DoctorTimeSlot objects (not yet saved)
        """
        from doctors.models import DoctorTimeSlot
        
        slots = []
        
        # Build time range
        start_datetime = datetime.combine(target_date, schedule.start_time)
        end_datetime = datetime.combine(target_date, schedule.end_time)
        
        # Define break range if exists
        break_start = None
        break_end = None
        if schedule.break_start_time and schedule.break_end_time:
            break_start = datetime.combine(target_date, schedule.break_start_time)
            break_end = datetime.combine(target_date, schedule.break_end_time)
        
        # Generate slots loop
        current = start_datetime
        slot_duration = timedelta(minutes=self.SLOT_DURATION_MINUTES)
        
        while current + slot_duration <= end_datetime:
            slot_start = current
            slot_end = current + slot_duration
            
            # Check if slot overlaps with break time
            if break_start and break_end:
                if ScheduleGeneratorService._time_ranges_overlap(slot_start, slot_end, break_start, break_end):
                    current += slot_duration
                    continue
            
            # Convert to UTC
            slot_start_utc = ScheduleGeneratorService._convert_to_utc(slot_start)
            slot_end_utc = ScheduleGeneratorService._convert_to_utc(slot_end)
            
            # Create slot object
            slot = DoctorTimeSlot(
                doctor=doctor,
                date=target_date,
                start_datetime=slot_start_utc,
                end_datetime=slot_end_utc,
                status='available'
            )
            slots.append(slot)
            
            current += slot_duration
        
        return slots
    
    @staticmethod
    def _time_ranges_overlap(start1, end1, start2, end2) -> bool:
        """
        Check if two time ranges overlap.
        
        Args:
            start1, end1: First time range
            start2, end2: Second time range
            
        Returns:
            bool: True if ranges overlap
        """
        return start1 < end2 and end1 > start2
    
    @staticmethod
    def _convert_to_utc(local_datetime):
        """
        Convert local datetime to UTC.
        
        Args:
            local_datetime: Local datetime object
            
        Returns:
            datetime: UTC datetime object
        """
        # Assuming server timezone is the same as doctor's local timezone
        # In production, this should be configurable per doctor
        local_tz = timezone.get_current_timezone()
        
        if local_datetime.tzinfo is None:
            local_datetime = timezone.make_aware(local_datetime, local_tz)
        
        return timezone.make_naive(local_datetime, timezone.UTC)
    
    @transaction.atomic
    def regenerate_slots_for_date_range(self, doctor, start_date: date, end_date: date) -> dict:
        """
        Regenerate slots for a date range.
        
        Args:
            doctor: Doctor instance
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            dict: Statistics about slot generation
        """
        stats = {
            'total_days': 0,
            'slots_generated': 0,
            'days_with_templates': 0,
            'days_without_templates': 0
        }
        
        current_date = start_date
        while current_date <= end_date:
            stats['total_days'] += 1
            
            try:
                slots_count = self.generate_daily_slots(doctor, current_date)
                stats['slots_generated'] += slots_count
                stats['days_with_templates'] += 1
            except ValueError:
                # No template exists for this weekday
                stats['days_without_templates'] += 1
            
            current_date += timedelta(days=1)
        
        return stats
    
    @staticmethod
    def get_available_slots_for_date(doctor, target_date: date) -> List:
        """
        Get available slots for a doctor on a specific date.
        
        Args:
            doctor: Doctor instance
            target_date: Date to check
            
        Returns:
            List: List of available DoctorTimeSlot objects
        """
        from doctors.models import DoctorTimeSlot
        
        return list(DoctorTimeSlot.objects.filter(
            doctor=doctor,
            date=target_date,
            status='available'
        ).order_by('start_datetime'))
    
    @staticmethod
    def book_slot(slot_id: int) -> bool:
        """
        Book a specific time slot.
        
        Args:
            slot_id: ID of the slot to book
            
        Returns:
            bool: True if booking successful, False if slot not available
        """
        from doctors.models import DoctorTimeSlot
        
        try:
            with transaction.atomic():
                slot = DoctorTimeSlot.objects.select_for_update().get(id=slot_id)
                
                if slot.status != 'available':
                    return False
                
                slot.status = 'booked'
                slot.save(update_fields=['status'])
                return True
                
        except DoctorTimeSlot.DoesNotExist:
            return False
    
    def generate_slots_for_all_doctors(self, start_date: date, end_date: date) -> dict:
        """
        Generate slots for all active doctors within a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            dict: Statistics about slot generation
        """
        from doctors.models import Doctor
        
        stats = {
            'total_doctors': 0,
            'doctors_processed': 0,
            'total_slots_generated': 0,
            'errors': []
        }
        
        active_doctors = Doctor.objects.filter(is_active=True)
        stats['total_doctors'] = active_doctors.count()
        
        for doctor in active_doctors:
            try:
                doctor_stats = self.regenerate_slots_for_date_range(doctor, start_date, end_date)
                stats['total_slots_generated'] += doctor_stats['slots_generated']
                stats['doctors_processed'] += 1
            except Exception as e:
                stats['errors'].append(f"Doctor {doctor}: {str(e)}")
        
        return stats
