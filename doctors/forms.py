from django import forms
from django.core.validators import EmailValidator, RegexValidator
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Doctor, Patient


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
