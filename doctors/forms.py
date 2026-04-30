from django import forms
from django.core.validators import EmailValidator, RegexValidator
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User
from .models import Doctor, Availability, DoctorSchedule, Patient


class CustomDaySelectWidget(forms.Select):
    """Custom select widget that styles already scheduled days"""
    
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        
        # Check if this option is already scheduled
        if label and "(Already Scheduled)" in label:
            # Add styling to make it look disabled
            option['attrs']['class'] = option['attrs'].get('class', '') + ' text-gray-400 bg-gray-50'
            option['attrs']['disabled'] = True
            
        return option

class DoctorForm(forms.ModelForm):
    """Form for creating and editing doctors - optimized for performance"""
    
    class Meta:
        model = Doctor
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender', 'blood_group',
            'email', 'phone', 'address', 'specialization', 'qualification', 'experience_years',
            'license_number', 'department', 'bio', 'is_active'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'family-name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'email'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'tel'}),
            'specialization': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add HTML5 validation attributes for better UX
        self.fields['email'].widget.attrs.update({'required': True})
        self.fields['license_number'].widget.attrs.update({'required': True})
        self.fields['specialization'].widget.attrs.update({'required': True})
        
        # Optimize field choices for better performance
        if 'specialization' in self.fields:
            self.fields['specialization'].choices = [
                ('', 'Select Specialization'),
                ('Cardiology', 'Cardiology'),
                ('Neurology', 'Neurology'),
                ('Orthopedics', 'Orthopedics'),
                ('Pediatrics', 'Pediatrics'),
                ('Psychiatry', 'Psychiatry'),
                ('Radiology', 'Radiology'),
                ('Surgery', 'Surgery'),
                ('General Practice', 'General Practice'),
            ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'blood_group': forms.Select(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'specialization': forms.TextInput(attrs={'class': 'form-control'}),
            'qualification': forms.TextInput(attrs={'class': 'form-control'}),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'license_number': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class AvailabilityForm(forms.ModelForm):
    """Form for creating doctor availability"""
    class Meta:
        model = Availability
        fields = ['day_of_week', 'start_time', 'end_time', 'is_active']
        widgets = {
            'day_of_week': forms.Select(attrs={'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class SlotGenerationForm(forms.Form):
    """Form for generating appointment slots"""
    doctor = forms.ModelChoiceField(
        queryset=Doctor.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select Doctor"
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        help_text="Start date for slot generation"
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        help_text="End date for slot generation"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Start date must be before end date")
        
        return cleaned_data


class DoctorScheduleForm(forms.ModelForm):
    """Form for creating and editing doctor schedules"""
    
    class Meta:
        model = DoctorSchedule
        fields = [
            'day_of_week', 'start_time', 'end_time', 'is_active', 'notes'
        ]
        widgets = {
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.doctor = kwargs.pop('doctor', None)
        super().__init__(*args, **kwargs)
        
        # Get existing scheduled days for this doctor
        existing_days = []
        if self.doctor:
            existing_schedules = DoctorSchedule.objects.filter(doctor=self.doctor)
            if self.instance and self.instance.pk:
                existing_schedules = existing_schedules.exclude(pk=self.instance.pk)
            existing_days = existing_schedules.values_list('day_of_week', flat=True)
        
        # Create day choices with unavailable days disabled
        day_choices = []
        for value, label in DoctorSchedule.DAY_CHOICES:
            if value in existing_days:
                # Add disabled option
                day_choices.append((value, f"{label} (Already Scheduled)"))
            else:
                # Add available option
                day_choices.append((value, label))
        
        # Override the day_of_week field with custom choices
        self.fields['day_of_week'] = forms.ChoiceField(
            choices=day_choices,
            widget=CustomDaySelectWidget(attrs={'class': 'form-control'}),
            label='Day of Week'
        )
        
        # Add custom CSS class for disabled options
        if existing_days:
            # We'll handle this in the template by checking the option text
            pass
        
        # Set initial value if editing
        if self.instance and self.instance.day_of_week:
            self.fields['day_of_week'].initial = self.instance.day_of_week
        
        self.fields['start_time'].label = 'Start Time'
        self.fields['end_time'].label = 'End Time'
        self.fields['is_active'].label = 'Active Schedule'
        self.fields['notes'].label = 'Notes (Optional)'
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        day_of_week = cleaned_data.get('day_of_week')
        
        if start_time and end_time:
            # Validate time logic
            if end_time <= start_time:
                raise forms.ValidationError('End time must be after start time.')
            
            # Validate that the time range is in 30-minute increments
            start_minutes = start_time.hour * 60 + start_time.minute
            end_minutes = end_time.hour * 60 + end_time.minute
            
            if start_minutes % 30 != 0:
                raise forms.ValidationError('Start time must be in 30-minute increments (e.g., 9:00, 9:30, 10:00).')
            
            if end_minutes % 30 != 0:
                raise forms.ValidationError('End time must be in 30-minute increments (e.g., 9:00, 9:30, 10:00).')
            
            # Minimum duration of 30 minutes
            total_minutes = end_minutes - start_minutes
            if end_minutes < start_minutes:  # Handle overnight
                total_minutes = (24 * 60) - start_minutes + end_minutes
            
            if total_minutes < 30:
                raise forms.ValidationError('Schedule duration must be at least 30 minutes.')
        
        # Check for duplicate day of week - prevent selection of already scheduled days
        if day_of_week and self.doctor:
            existing_schedules = DoctorSchedule.objects.filter(
                doctor=self.doctor,
                day_of_week=day_of_week
            )
            if self.instance and self.instance.pk:
                existing_schedules = existing_schedules.exclude(pk=self.instance.pk)
            
            if existing_schedules.exists():
                day_name = dict(DoctorSchedule.DAY_CHOICES).get(day_of_week, day_of_week)
                raise forms.ValidationError(f'{day_name} is already scheduled for this doctor. Please choose a different day.')
        
        return cleaned_data


class PatientRegistrationForm(forms.ModelForm):
    """Form for patient registration"""
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter password'
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Confirm password'
    }))
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Username'
        self.fields['email'].label = 'Email Address'
        self.fields['first_name'].label = 'First Name'
        self.fields['last_name'].label = 'Last Name'
        self.fields['password'].label = 'Password'
        self.fields['confirm_password'].label = 'Confirm Password'
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError('Passwords do not match.')
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            # Create patient profile
            Patient.objects.create(user=user)
        return user
