from django import forms
from django.core.validators import EmailValidator, RegexValidator
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User
from .models import Doctor, DoctorSchedule, Patient


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
    """Form for creating and editing doctor schedules - NEW ARCHITECTURE"""
    
    class Meta:
        model = DoctorSchedule
        fields = [
            'day_of_week', 'start_time', 'end_time', 'slot_duration', 'is_active'
        ]
        widgets = {
            'day_of_week': forms.Select(attrs={'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'slot_duration': forms.NumberInput(attrs={'class': 'form-control', 'min': 15, 'max': 240, 'step': 15}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.doctor = kwargs.pop('doctor', None)
        super().__init__(*args, **kwargs)
        
        # Set labels
        self.fields['day_of_week'].label = 'Day of Week'
        self.fields['start_time'].label = 'Start Time'
        self.fields['end_time'].label = 'End Time'
        self.fields['slot_duration'].label = 'Slot Duration (minutes)'
        self.fields['is_active'].label = 'Active Schedule'
        
        # Set help text
        self.fields['slot_duration'].help_text = 'Duration for each appointment slot (15-240 minutes)'
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        day_of_week = cleaned_data.get('day_of_week')
        slot_duration = cleaned_data.get('slot_duration')
        
        if start_time and end_time:
            # Validate time logic
            if end_time <= start_time:
                raise forms.ValidationError('End time must be after start time.')
            
            # Minimum duration of 30 minutes
            start_minutes = start_time.hour * 60 + start_time.minute
            end_minutes = end_time.hour * 60 + end_time.minute
            total_minutes = end_minutes - start_minutes
            
            if total_minutes < 30:
                raise forms.ValidationError('Schedule duration must be at least 30 minutes.')
        
        # Validate slot duration
        if slot_duration:
            if slot_duration < 15 or slot_duration > 240:
                raise forms.ValidationError('Slot duration must be between 15 and 240 minutes.')
            if slot_duration % 15 != 0:
                raise forms.ValidationError('Slot duration must be in 15-minute increments.')
        
        # Check for duplicate day of week
        if day_of_week is not None and self.doctor:
            existing_schedules = DoctorSchedule.objects.filter(
                doctor=self.doctor,
                day_of_week=day_of_week
            )
            if self.instance and self.instance.pk:
                existing_schedules = existing_schedules.exclude(pk=self.instance.pk)
            
            if existing_schedules.exists():
                day_name = dict(DoctorSchedule.DAYS).get(day_of_week, f'Day {day_of_week}')
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
