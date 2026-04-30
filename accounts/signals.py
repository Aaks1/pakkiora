from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .default_admin import ensure_default_superuser


@receiver(post_migrate)
def create_default_admin_after_migrate(**kwargs):
    ensure_default_superuser()
