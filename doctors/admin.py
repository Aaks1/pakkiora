from django.contrib import admin
from django.utils import timezone
from django.contrib import messages
from datetime import datetime, timedelta
from .models import Doctor, Patient, Appointment, DoctorAvailability


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'specialization', 'license_number', 'is_active']
    list_filter = ['is_active', 'specialization', 'department']
    search_fields = ['first_name', 'last_name', 'specialization', 'license_number']
    readonly_fields = ['created_at', 'updated_at']




@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'date', 'is_available', 'created_at']
    list_filter = ['is_available', 'date', 'doctor']
    search_fields = ['doctor__first_name', 'doctor__last_name', 'notes']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('doctor', 'date', 'is_available')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )
    
    actions = ['mark_as_available', 'mark_as_unavailable', 'delete_past_availability']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('doctor')
    
    def mark_as_available(self, request, queryset):
        """Mark selected availability as available"""
        updated = queryset.update(is_available=True)
        self.message_user(request, f"Marked {updated} dates as available")
    mark_as_available.short_description = "Mark selected dates as available"
    
    def mark_as_unavailable(self, request, queryset):
        """Mark selected availability as unavailable"""
        updated = queryset.update(is_available=False)
        self.message_user(request, f"Marked {updated} dates as unavailable")
    mark_as_unavailable.short_description = "Mark selected dates as unavailable"
    
    def delete_past_availability(self, request, queryset):
        """Delete past availability records"""
        today = timezone.now().date()
        past_availability = queryset.filter(date__lt=today)
        count = past_availability.count()
        past_availability.delete()
        self.message_user(request, f"Deleted {count} past availability records")
    delete_past_availability.short_description = "Delete past availability"


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
