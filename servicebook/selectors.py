from django.db.models import Count
from dynamic_preferences.registries import global_preferences_registry
from members.models import Member
from .models import Service, Attendance
from collections import Counter

global_preferences = global_preferences_registry.manager()


def get_services_list():
    return Service.objects.all().order_by('-start')

def get_attandance_list():
    return Attendance.objects.all()


def get_services_of_member(member: Member):
    return Attendance.objects.filter(person=member).order_by('service__start')

def get_number_of_services(member: Member, state):
    return Attendance.objects.filter(person=member, state=state).count()

def get_summary_of_attendances_per_service(service: Service):
    return {
        'A': Attendance.objects.filter(service=service, state="A").count(),
        'E': Attendance.objects.filter(service=service, state="E").count(),
        'F': Attendance.objects.filter(service=service, state="F").count(),
    }

def get_top_lists_by_state(state, max_entries=7):
    return  Attendance.objects.filter(state=state) \
        .values('person__name', 'person__lastname') \
        .annotate(num_services=Count('person')) \
        .order_by('-num_services')[:max_entries]

def get_attandance_alert_by_member(member: Member, n_not_present=5, n_last_items=10):
    """
    Determines if a member should receive an attendance alert based on their attendance record.

    Args:
        member (Member): The member whose attendance is being checked.
        n_not_present (int, optional): The threshold number of non-present states to trigger an alert. Defaults to 5.
        n_last_items (int, optional): The number of most recent attendance records to check. Defaults to 10.

    Returns:
        bool: True if the member's non-present states meet or exceed the threshold, False otherwise.
    """
    n_not_present = global_preferences['members__alert_threshold']
    n_last_items = global_preferences['members__alert_threshold_last_entries']
    services = Attendance.objects.filter(person=member).order_by('-service__start')[:n_last_items]\
        .values_list('state', flat=True)
    c = Counter(services)
    failed = c['F'] + c['E']
    return failed >= n_not_present