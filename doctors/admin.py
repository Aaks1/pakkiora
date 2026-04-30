from django.contrib import admin
from django.utils import timezone
from django.contrib import messages
from datetime import datetime, timedelta
from .models import Doctor, DoctorSchedule, Patient, Appointment


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'specialization', 'license_number', 'is_active']
    list_filter = ['is_active', 'specialization', 'department']
    search_fields = ['first_name', 'last_name', 'specialization', 'license_number']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'get_day_of_week_display', 'start_time', 'end_time', 'slot_duration', 'is_active']
    list_filter = ['day_of_week', 'is_active']
    search_fields = ['doctor__first_name', 'doctor__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('doctor', 'day_of_week', 'is_active')
        }),
        ('Schedule Times', {
            'fields': ('start_time', 'end_time', 'slot_duration')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )


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
    search_fields = ['patient__user__username', 'doctor__first_name', 'doctor__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['mark_as_completed', 'mark_as_no_show']
    
    def mark_as_completed(self, request, queryset):
        """Mark selected appointments as completed"""
        updated = queryset.update(status='completed')
        self.message_user(request, f"Marked {updated} appointments as completed")
    mark_as_completed.short_description = "Mark selected appointments as completed"
    
    def mark_as_no_show(self, request, queryset):
        """Mark selected appointments as no show"""
        updated = queryset.update(status='cancelled')
        self.message_user(request, f"Marked {updated} appointments as cancelled")
    mark_as_no_show.short_description = "Mark selected appointments as cancelled"
