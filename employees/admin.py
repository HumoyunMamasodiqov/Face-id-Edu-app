from django.contrib import admin
from .models import Employee, Attendance, MonthlySalary

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'position', 'department', 'monthly_salary', 'is_active')
    list_filter = ('department', 'is_active', 'position')
    search_fields = ('first_name', 'last_name', 'position', 'department')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Shaxsiy ma\'lumotlar', {
            'fields': ('first_name', 'last_name', 'photo')
        }),
        ('Ish ma\'lumotlari', {
            'fields': ('position', 'department', 'monthly_salary')
        }),
        ('Ish jadvali', {
            'fields': ('work_days', 'work_schedule', 'daily_work_hours')
        }),
        ('Jarimalar', {
            'fields': ('late_penalty_per_minute', 'allowed_late_minutes')
        }),
        ('Aloqa', {
            'fields': ('phone', 'email')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at')
        }),
    )

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'time', 'type_display', 'status', 'late_minutes', 'penalty_amount')
    list_filter = ('date', 'type', 'status', 'employee__department')
    search_fields = ('employee__first_name', 'employee__last_name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'date'

@admin.register(MonthlySalary)
class MonthlySalaryAdmin(admin.ModelAdmin):
    list_display = ('employee', 'year', 'month', 'net_salary', 'total_penalty', 'is_paid')
    list_filter = ('year', 'month', 'is_paid', 'employee__department')
    search_fields = ('employee__first_name', 'employee__last_name')
    readonly_fields = ('created_at', 'updated_at')