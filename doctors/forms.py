from django import forms
from django.contrib.auth.models import User
from .models import Doctor, Patient


class AddDoctorForm(forms.ModelForm):
    """Form for adding doctor profile and schedule only."""
    SPECIALIZATION_CHOICES = [
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
    ]
    
    # Doctor Details
    specialization = forms.ChoiceField(
        choices=SPECIALIZATION_CHOICES,
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
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '09:00,10:30,14:00'
        }),
        required=False,
        help_text='Enter time slots separated by commas. Use 24-hour format e.g. 09:00,10:30,14:00'
    )
    
    class Meta:
        model = Doctor
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'address',
            'qualification', 'experience_years', 'license_number', 'department', 'bio'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'required': True, 'placeholder': 'doctor@clinic.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'required': True, 'placeholder': '9876543210'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Clinic address'}),
            'qualification': forms.TextInput(attrs={'class': 'form-control', 'required': True, 'placeholder': 'MD, MS, MBBS, etc.'}),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'license_number': forms.TextInput(attrs={'class': 'form-control', 'required': True, 'placeholder': 'MED-REG-12345'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Cardiac Care'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Short professional bio'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].label = 'First Name'
        self.fields['last_name'].label = 'Last Name'
        self.fields['email'].label = 'Email'
        self.fields['phone'].label = 'Phone'
        self.fields['address'].label = 'Address'
        self.fields['qualification'].label = 'Qualification'
        self.fields['experience_years'].label = 'Experience (Years)'
        self.fields['license_number'].label = 'License Number'
        self.fields['department'].label = 'Department'
        self.fields['bio'].label = 'Biography'
        self.fields['time_slots'].label = 'Slots'
        
        # Make required fields
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
        self.fields['phone'].required = True
        self.fields['license_number'].required = True
        self.fields['specialization'].required = True
        self.fields['email'].help_text = 'Must be unique across doctors.'
        self.fields['license_number'].help_text = 'Use official medical registration number.'
        self.fields['available_days'].help_text = 'Select at least one recurring day.'
        self.fields['time_slots'].help_text = 'Comma-separated 24h times, for example: 09:00,09:30,10:00'

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if Doctor.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('A doctor with this email already exists.')
        return email

    def clean_license_number(self):
        license_number = (self.cleaned_data.get('license_number') or '').strip()
        if Doctor.objects.filter(license_number__iexact=license_number).exists():
            raise forms.ValidationError('A doctor with this license number already exists.')
        return license_number

    def clean_available_days(self):
        days = self.cleaned_data.get('available_days') or []
        if not days:
            raise forms.ValidationError('Please select at least one available day.')
        return days
    
    def clean_time_slots(self):
        time_slots = self.cleaned_data.get('time_slots', '')
        if time_slots:
            slots = [s.strip() for s in time_slots.split(',') if s.strip()]
            parsed = []
            for slot in slots:
                try:
                    from datetime import datetime
                    parsed_time = datetime.strptime(slot, '%H:%M').time()
                    parsed.append(parsed_time.strftime('%H:%M'))
                except ValueError:
                    raise forms.ValidationError(f'Invalid time format: "{slot}". Use HH:MM format e.g. 09:00')
            # Keep a clean, sorted, de-duplicated slot list.
            unique_sorted = sorted(set(parsed))
            return ','.join(unique_sorted)
        raise forms.ValidationError('Please provide at least one time slot.')
    
    def save(self, commit=True):
        # Create doctor profile
        doctor = super().save(commit=False)

        # Store available_days as list in JSONField
        doctor.available_days = self.cleaned_data.get('available_days', [])

        # Store time_slots as comma-separated string
        doctor.time_slots = self.cleaned_data.get('time_slots', '')

        if commit:
            doctor.save()

        return doctor


class DoctorUpdateForm(forms.ModelForm):
    """Form for updating existing doctor profile data."""
    available_days = forms.MultipleChoiceField(
        choices=Doctor.DAY_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False
    )

    class Meta:
        model = Doctor
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone',
            'address',
            'specialization',
            'qualification',
            'experience_years',
            'license_number',
            'department',
            'bio',
            'available_days',
            'time_slots',
            'is_active',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'required': True}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'specialization': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'qualification': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'license_number': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'time_slots': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '09:00,10:30,14:00'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['available_days'].initial = self.instance.available_days

    def clean_time_slots(self):
        time_slots = self.cleaned_data.get('time_slots', '')
        if time_slots:
            slots = [s.strip() for s in time_slots.split(',') if s.strip()]
            for slot in slots:
                try:
                    from datetime import datetime
                    datetime.strptime(slot, '%H:%M')
                except ValueError:
                    raise forms.ValidationError(f'Invalid time format: "{slot}". Use HH:MM format e.g. 09:00')
        return time_slots






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
