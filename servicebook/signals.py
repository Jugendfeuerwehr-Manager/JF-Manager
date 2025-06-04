from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Service, Attendance


def invalidate_attendance_cache():
    """Invalidate the attendance over time data cache"""
    cache_key = 'attendance_over_time_data'
    cache.delete(cache_key)


@receiver(post_save, sender=Service)
def service_saved(sender, instance, **kwargs):
    """Invalidate cache when a service is created or updated"""
    invalidate_attendance_cache()


@receiver(post_delete, sender=Service)
def service_deleted(sender, instance, **kwargs):
    """Invalidate cache when a service is deleted"""
    invalidate_attendance_cache()


@receiver(post_save, sender=Attendance)
def attendance_saved(sender, instance, **kwargs):
    """Invalidate cache when an attendance record is created or updated"""
    invalidate_attendance_cache()


@receiver(post_delete, sender=Attendance)
def attendance_deleted(sender, instance, **kwargs):
    """Invalidate cache when an attendance record is deleted"""
    invalidate_attendance_cache()
