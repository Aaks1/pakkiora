from django import forms
from django.core.validators import EmailValidator, RegexValidator
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Doctor, Patient, DoctorAvailability


class AddDoctorForm(forms.ModelForm):
    """Comprehensive form for adding doctors with account details and schedule"""
    
    # Account Details
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter username',
            'required': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password',
            'required': True
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password',
            'required': True
        })
    )
    
    # Doctor Details
    specialization = forms.ChoiceField(
        choices=[
            ('', 'Select Specialization'),
            ('Cardiology', 'Cardiology'),
            ('Neurology', 'Neurology'),
            ('Orthopedics', 'Orthopedics'),
            ('Pediatrics', 'Pediatrics'),
            ('Psychiatry', 'Psychiatry'),
            ('Radiology', 'Radiology'),
            ('Surgery', 'Surgery'),
            ('General Practice', 'General Practice'),
            ('Dermatology', 'Dermatology'),
            ('Ophthalmology', 'Ophthalmology'),
            ('ENT', 'ENT'),
            ('Gynecology', 'Gynecology'),
        ],
        widget=forms.Select(attrs={'class': 'form-control', 'required': True})
    )
    
    # Available Days
    available_days = forms.MultipleChoiceField(
        choices=[
            ('monday', 'Monday'),
            ('tuesday', 'Tuesday'),
            ('wednesday', 'Wednesday'),
            ('thursday', 'Thursday'),
            ('friday', 'Friday'),
            ('saturday', 'Saturday'),
            ('sunday', 'Sunday'),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False
    )
    
    # Time Slots
    time_slots = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': '09:00, 10:30, 14:00, 15:30',
            'help_text': 'Enter time slots separated by commas. Use 24-hour format e.g. 09:00,10:30,14:00'
        }),
        required=False,
        help_text='Enter time slots separated by commas. Use 24-hour format e.g. 09:00,10:30,14:00'
    )
    
    class Meta:
        model = Doctor
        fields = [
            'first_name', 'last_name', 'email', 'date_of_birth', 'phone', 'address',
            'qualification', 'experience_years', 'license_number', 'department', 'bio'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'required': True}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'qualification': forms.TextInput(attrs={'class': 'form-control'}),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'license_number': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].label = 'First Name'
        self.fields['last_name'].label = 'Last Name'
        self.fields['email'].label = 'Email'
        self.fields['date_of_birth'].label = 'Date of Birth'
        self.fields['phone'].label = 'Phone'
        self.fields['address'].label = 'Address'
        self.fields['qualification'].label = 'Qualification'
        self.fields['experience_years'].label = 'Experience Years'
        self.fields['license_number'].label = 'License Number'
        self.fields['department'].label = 'Department'
        self.fields['bio'].label = 'Bio'
        
        # Make required fields
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
        self.fields['specialization'].required = True
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Username already exists.')
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already exists.')
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError('Passwords do not match.')
        
        return cleaned_data
    
    def save(self, commit=True):
        # Create user account
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name']
        )
        
        # Create doctor profile
        doctor = super().save(commit=False)
        doctor.user = user
        if commit:
            doctor.save()
            
            # Create availability based on available days and time slots
            available_days = self.cleaned_data.get('available_days', [])
            time_slots = self.cleaned_data.get('time_slots', '')
            
            if available_days and time_slots:
                # Parse time slots
                slot_list = [slot.strip() for slot in time_slots.split(',') if slot.strip()]
                
                # Create availability for next 30 days
                from datetime import datetime, timedelta
                today = timezone.now().date()
                
                for i in range(30):
                    date = today + timedelta(days=i)
                    day_name = date.strftime('%A').lower()
                    
                    if day_name in available_days:
                        for slot in slot_list:
                            try:
                                # Parse time slot
                                time_obj = datetime.strptime(slot, '%H:%M').time()
                                
                                # Create availability for this time slot
                                DoctorAvailability.objects.create(
                                    doctor=doctor,
                                    date=date,
                                    start_time=time_obj,
                                    end_time=(datetime.combine(date, time_obj) + timedelta(minutes=30)).time(),
                                    is_available=True
                                )
                            except ValueError:
                                continue  # Skip invalid time formats
        
        return doctor


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




class DoctorAvailabilityForm(forms.ModelForm):
    """Form for managing doctor availability"""
    
    class Meta:
        model = DoctorAvailability
        fields = ['date', 'is_available', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].label = 'Date'
        self.fields['is_available'].label = 'Available'
        self.fields['notes'].label = 'Notes (Optional)'
        self.fields['notes'].help_text = 'Optional notes for this date'
    
    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        
        # Prevent creating availability for past dates
        if date and date < timezone.now().date():
            raise forms.ValidationError('Cannot set availability for past dates.')
        
        return cleaned_data


class MultiDateAvailabilityForm(forms.Form):
    """Form for managing multiple dates at once"""
    doctor = forms.ModelChoiceField(
        queryset=Doctor.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select Doctor"
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['doctor'].label = 'Doctor'
        self.fields['start_date'].label = 'Start Date'
        self.fields['end_date'].label = 'End Date'
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError("End date must be after start date.")
            
            # Prevent creating availability for past dates
            if start_date < timezone.now().date():
                raise forms.ValidationError("Cannot set availability for past dates.")
        
        return cleaned_data
    
    def save_availability(self):
        """Save availability for the date range"""
        doctor = self.cleaned_data['doctor']
        start_date = self.cleaned_data['start_date']
        end_date = self.cleaned_data['end_date']
        
        availabilities_created = []
        current_date = start_date
        
        while current_date <= end_date:
            availability, created = DoctorAvailability.objects.get_or_create(
                doctor=doctor,
                date=current_date,
                defaults={'is_available': True}
            )
            if created:
                availabilities_created.append(availability)
            current_date += timezone.timedelta(days=1)
        
        return availabilities_created


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
