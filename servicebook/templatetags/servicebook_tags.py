from django import template
from ..selectors import get_summary_of_attendances_per_service

register = template.Library()

@register.simple_tag
def get_attendance_summary(service):
    """Get attendance summary for a service"""
    return get_summary_of_attendances_per_service(service)
