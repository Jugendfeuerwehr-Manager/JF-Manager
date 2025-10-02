from .models import Member, Parent, Event

def get_members_list():
    return Member.objects.all().order_by('lastname')

def get_parent_list():
    return Parent.objects.all().order_by('lastname')

def get_events_list():
    return Event.objects.all().order_by('datetime')