from django.db.models import Count, Case, When, IntegerField
from django.core.cache import cache
from dynamic_preferences.registries import global_preferences_registry
from members.models import Member
from .models import Service, Attendance
from collections import Counter

global_preferences = global_preferences_registry.manager()


def get_services_list():
    """Get services list with optimized prefetch for better performance."""
    return Service.objects.select_related().prefetch_related(
        'operations_manager',
        'attendance_set'
    ).order_by('-start')

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

def get_attendance_over_time_data():
    """
    Get attendance data over time for chart visualization.
    Returns:
        dict: Contains service_labels, service_dates and attendance counts for A, E, F
    """
    # Try to get cached data first
    cache_key = 'attendance_over_time_data'
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data

    # Get recent services ordered chronologically (oldest first for timeline)
    services = Service.objects.all().order_by('start')
    
    if not services:
        empty_data = {
            'service_labels': [],
            'service_dates': [],
            'attendance_data': {
                'A': [],
                'E': [],
                'F': []
            }
        }
        # Cache empty result for 5 minutes
        cache.set(cache_key, empty_data, 300)
        return empty_data

    # Optimize database queries by getting all attendance data in one query
    # and then aggregating it per service in Python
    attendance_data = Attendance.objects.filter(
        service__in=services
    ).values('service_id', 'state').annotate(
        count=Count('id')
    )
    
    # Create a lookup dictionary for attendance counts per service
    attendance_lookup = {}
    for item in attendance_data:
        service_id = item['service_id']
        state = item['state']
        count = item['count']
        
        if service_id not in attendance_lookup:
            attendance_lookup[service_id] = {'A': 0, 'E': 0, 'F': 0}
        
        attendance_lookup[service_id][state] = count

    service_labels = []
    service_dates = []
    attendance_a = []
    attendance_e = []
    attendance_f = []
    
    for service in services:
        # Create label for the service
        date_str = service.start.strftime('%d.%m.%Y')
        topic = service.topic or 'Kein Thema'
        if len(topic) > 20:
            topic = topic[:17] + '...'
        service_labels.append(f"{date_str}")
        service_dates.append(service.start.strftime('%Y-%m-%d'))
        
        # Get attendance counts for this service from our lookup
        counts = attendance_lookup.get(service.id, {'A': 0, 'E': 0, 'F': 0})
        attendance_a.append(counts['A'])
        attendance_e.append(counts['E']) 
        attendance_f.append(counts['F'])

    result = {
        'service_labels': service_labels,
        'service_dates': service_dates,
        'attendance_data': {
            'A': attendance_a,
            'E': attendance_e,
            'F': attendance_f
        }
    }
    
    # Cache result for 7 days (604800 seconds) since data only changes 1-2 times per week
    cache.set(cache_key, result, 604800)
    
    return result

def invalidate_attendance_over_time_cache():
    """
    Utility function to manually invalidate the attendance over time cache.
    Can be called from management commands or other parts of the application.
    """
    cache_key = 'attendance_over_time_data'
    cache.delete(cache_key)
    return cache_key

def get_services_with_attendance_summary():
    """
    Get services list with pre-calculated attendance summaries for better performance.
    This avoids N+1 queries by calculating all attendance summaries in bulk.
    """
    from django.db.models import Count, Case, When, IntegerField
    
    # Get services with prefetched relations
    services = Service.objects.select_related().prefetch_related(
        'operations_manager',
        'attendance_set'
    ).order_by('-start')
    
    # Pre-calculate attendance summaries for all services in bulk
    attendance_summaries = {}
    if services:
        # Get all attendance data for these services in one query
        attendance_data = Attendance.objects.filter(
            service__in=services
        ).values('service_id', 'state').annotate(
            count=Count('id')
        )
        
        # Organize by service_id and state
        for item in attendance_data:
            service_id = item['service_id']
            state = item['state']
            count = item['count']
            
            if service_id not in attendance_summaries:
                attendance_summaries[service_id] = {'A': 0, 'E': 0, 'F': 0}
            
            attendance_summaries[service_id][state] = count
    
    # Attach attendance summaries to services
    for service in services:
        service.attendance_summary = attendance_summaries.get(
            service.id, 
            {'A': 0, 'E': 0, 'F': 0}
        )
    
    return services

# Cache invalidation functions
def invalidate_service_caches():
    """Invalidate all service-related caches when data changes."""
    from django.core.cache import cache
    cache.delete('attendance_over_time_data')
    # Add more cache keys here as needed
    
def get_services_with_attendance_summary_paginated(page_size=50):
    """
    Get paginated services list with pre-calculated attendance summaries.
    This helps with very large datasets by limiting initial rendering.
    """
    from django.core.paginator import Paginator
    
    services = get_services_with_attendance_summary()
    paginator = Paginator(services, page_size)
    
    return paginator