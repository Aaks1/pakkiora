from django.contrib.auth.models import User


DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"


def ensure_default_superuser():
    """Ensure default Django superuser exists and is active."""
    user, created = User.objects.get_or_create(
        username=DEFAULT_ADMIN_USERNAME,
        defaults={
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
            "email": "",
            "first_name": "Default",
            "last_name": "Admin",
        },
    )

    updated = False
    if not user.is_staff:
        user.is_staff = True
        updated = True
    if not user.is_superuser:
        user.is_superuser = True
        updated = True
    if not user.is_active:
        user.is_active = True
        updated = True

    # Keep deterministic credentials for bootstrap superuser.
    user.set_password(DEFAULT_ADMIN_PASSWORD)
    updated = True

    if created or updated:
        user.save()

    return user
