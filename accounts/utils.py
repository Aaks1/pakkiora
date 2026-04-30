import random
import string
from django.utils.text import slugify

def generate_password_from_name(first_name, last_name):

    return generate_username_from_name(first_name, last_name)

def generate_secure_password_from_name(first_name, last_name):
    """
    Generate a secure random password based on the user's name
    Format: [first_name][random_number][last_name_initial][random_chars]
    Example: john123S!x
    """
    # Get the first 3 letters of first name (lowercase)
    name_part = slugify(first_name)[:3].lower()
    
    # Generate a random number between 100-999
    random_number = random.randint(100, 999)
    
    # Get last name initial (uppercase)
    last_initial = last_name[0].upper() if last_name else 'X'
    
    # Generate random special characters
    special_chars = '!@#$%^&*'
    random_special = random.choice(special_chars)
    
    # Generate random lowercase letters
    random_letters = ''.join(random.choices(string.ascii_lowercase, k=2))
    
    # Combine all parts
    password = f"{name_part}{random_number}{last_initial}{random_special}{random_letters}"
    
    return password

def generate_secure_password(length=12):
    """
    Generate a secure random password with mixed characters
    """
    characters = string.ascii_letters + string.digits + '!@#$%^&*'
    password = ''.join(random.choices(characters, k=length))
    return password

def generate_username_from_name(first_name, last_name):
    """
    Generate a username from first and last name
    Format: firstname.lastname
    """
    username = f"{slugify(first_name)}.{slugify(last_name)}".lower()
    return username


"""
Optimized authentication utilities for better performance
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from doctors.models import Patient

User = get_user_model()


def get_user_with_profile(user_id=None, username=None, email=None):
    """
    Optimized user lookup with profile in single query
    Uses caching for frequently accessed users
    """
    cache_key = None
    
    if user_id:
        cache_key = f'user_profile_{user_id}'
        lookup_kwargs = {'id': user_id}
    elif username:
        cache_key = f'user_profile_username_{username}'
        lookup_kwargs = {'username': username}
    elif email:
        cache_key = f'user_profile_email_{email}'
        lookup_kwargs = {'email': email}
    else:
        return None
    
    # Try cache first
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    # Use select_related to fetch user and patient profile in single query
    try:
        user = User.objects.select_related('patient').get(**lookup_kwargs)
        result = {
            'user': user,
            'patient': getattr(user, 'patient', None),
            'has_profile': hasattr(user, 'patient')
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, result, 300)
        return result
        
    except User.DoesNotExist:
        result = {'user': None, 'patient': None, 'has_profile': False}
        cache.set(cache_key, result, 60)  # Cache negative result for 1 minute
        return result


def invalidate_user_cache(user_id=None, username=None, email=None):
    """Invalidate cached user data"""
    cache_keys = []
    
    if user_id:
        cache_keys.append(f'user_profile_{user_id}')
    if username:
        cache_keys.append(f'user_profile_username_{username}')
    if email:
        cache_keys.append(f'user_profile_email_{email}')
    
    cache.delete_many(cache_keys)


def create_user_with_profile(user_data, patient_data):
    """
    Optimized user and patient creation using transaction
    """
    with transaction.atomic():
        # Create user first
        user = User.objects.create_user(**user_data)
        
        # Create patient profile
        patient = Patient.objects.create(user=user, **patient_data)
        
        # Invalidate cache
        invalidate_user_cache(user_id=user.id)
        
        return user, patient


def bulk_user_lookup(user_ids):
    """
    Optimized bulk user lookup for admin operations
    """
    return User.objects.filter(id__in=user_ids).select_related('patient').only(
        'id', 'username', 'first_name', 'last_name', 'email', 
        'is_staff', 'is_active', 'date_joined',
        'patient__id', 'patient__first_name', 'patient__last_name'
    )


def optimize_admin_queryset():
    """
    Return optimized queryset for admin operations
    """
    return User.objects.filter(is_staff=True).only(
        'id', 'username', 'first_name', 'last_name', 'email',
        'is_active', 'date_joined'
    ).select_related('patient')


def optimize_doctor_queryset():
    """
    Return optimized queryset for doctor operations
    """
    from .models import Doctor
    return Doctor.objects.all().only(
        'id', 'first_name', 'last_name', 'email', 'specialization',
        'department', 'license_number', 'is_active', 'created_at'
    )
