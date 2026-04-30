from django.contrib import admin
from django.utils import timezone
from django.contrib import messages
from datetime import datetime, timedelta
from .models import Doctor, Availability, DoctorSchedule, DoctorTimeSlot, Patient, Appointment


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'specialization', 'license_number', 'is_active']
    list_filter = ['is_active', 'specialization', 'department']
    search_fields = ['first_name', 'last_name', 'specialization', 'license_number']
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['generate_slots_next_7_days', 'generate_slots_next_30_days']
    
    def generate_slots_next_7_days(self, request, queryset):
        """Generate slots for selected doctors for next 7 days"""
        from appointments.schedule_generator import ScheduleGeneratorService
        
        schedule_service = ScheduleGeneratorService()
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=7)
        
        total_slots = 0
        for doctor in queryset:
            try:
                stats = schedule_service.regenerate_slots_for_date_range(doctor, start_date, end_date)
                total_slots += stats['slots_generated']
                self.message_user(request, f"Generated {stats['slots_generated']} slots for Dr. {doctor.first_name} {doctor.last_name}")
            except Exception as e:
                self.message_user(request, f"Error generating slots for Dr. {doctor.first_name} {doctor.last_name}: {str(e)}", level='error')
        
        self.message_user(request, f"Total slots generated: {total_slots}")
    generate_slots_next_7_days.short_description = "Generate slots for next 7 days"
    
    def generate_slots_next_30_days(self, request, queryset):
        """Generate slots for selected doctors for next 30 days"""
        from appointments.schedule_generator import ScheduleGeneratorService
        
        schedule_service = ScheduleGeneratorService()
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=30)
        
        total_slots = 0
        for doctor in queryset:
            try:
                stats = schedule_service.regenerate_slots_for_date_range(doctor, start_date, end_date)
                total_slots += stats['slots_generated']
                self.message_user(request, f"Generated {stats['slots_generated']} slots for Dr. {doctor.first_name} {doctor.last_name}")
            except Exception as e:
                self.message_user(request, f"Error generating slots for Dr. {doctor.first_name} {doctor.last_name}: {str(e)}", level='error')
        
        self.message_user(request, f"Total slots generated: {total_slots}")
    generate_slots_next_30_days.short_description = "Generate slots for next 30 days"


@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'day_of_week', 'start_time', 'end_time', 'break_start_time', 'break_end_time', 'is_active']
    list_filter = ['day_of_week', 'is_active']
    search_fields = ['doctor__first_name', 'doctor__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('doctor', 'day_of_week', 'is_active')
        }),
        ('Schedule Times', {
            'fields': ('start_time', 'end_time')
        }),
        ('Break Time (Optional)', {
            'fields': ('break_start_time', 'break_end_time'),
            'description': 'Optional break period during which no slots will be generated'
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at')
        })
    )


@admin.register(DoctorTimeSlot)
class DoctorTimeSlotAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'date', 'local_start_time', 'local_end_time', 'status', 'created_at']
    list_filter = ['status', 'date', 'doctor']
    search_fields = ['doctor__first_name', 'doctor__last_name']
    readonly_fields = ['created_at', 'start_datetime', 'end_datetime']
    
    actions = ['mark_as_available', 'mark_as_blocked']
    
    def mark_as_available(self, request, queryset):
        """Mark selected slots as available"""
        updated = queryset.update(status='available')
        self.message_user(request, f"Marked {updated} slots as available")
    mark_as_available.short_description = "Mark selected slots as available"
    
    def mark_as_blocked(self, request, queryset):
        """Mark selected slots as blocked"""
        updated = queryset.update(status='blocked')
        self.message_user(request, f"Marked {updated} slots as blocked")
    mark_as_blocked.short_description = "Mark selected slots as blocked"


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['user', 'first_name', 'last_name', 'phone', 'is_active']
    list_filter = ['is_active', 'gender', 'blood_group']
    search_fields = ['first_name', 'last_name', 'user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'date', 'start_time', 'end_time', 'status', 'created_at']
    list_filter = ['status', 'date', 'doctor']
    search_fields = ['patient__username', 'doctor__first_name', 'doctor__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['mark_as_completed', 'mark_as_no_show']
    
    def mark_as_completed(self, request, queryset):
        """Mark selected appointments as completed"""
        updated = queryset.update(status='COMPLETED')
        self.message_user(request, f"Marked {updated} appointments as completed")
    mark_as_completed.short_description = "Mark selected appointments as completed"
    
    def mark_as_no_show(self, request, queryset):
        """Mark selected appointments as no show"""
        updated = queryset.update(status='NO_SHOW')
        self.message_user(request, f"Marked {updated} appointments as no show")
    mark_as_no_show.short_description = "Mark selected appointments as no show"


# Hide old Availability model from admin (deprecated)
class HiddenModelAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return False  # Hide from non-superusers
    
    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def has_add_permission(self, request):
        return False  # Prevent adding through Django Admin
    
    def has_change_permission(self, request, obj=None):
        return False  # Prevent editing through Django Admin
    
    def has_delete_permission(self, request, obj=None):
        return False  # Prevent deleting through Django Admin

# Register deprecated models as hidden
admin.site.register(Availability, HiddenModelAdmin)
