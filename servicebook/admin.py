from django.contrib import admin
from .models import Attendance, Service
# Register your models here.

class AttendanceInline(admin.TabularInline):
    model = Attendance
    extra = 1


@admin.register(Service)
class DepartmentAdmin(admin.ModelAdmin):
    inlines = (AttendanceInline, )
    list_display = ('start','topic',)
    list_filter = ('start','topic')