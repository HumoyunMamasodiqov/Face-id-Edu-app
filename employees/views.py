# views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from datetime import date, datetime, time, timedelta
import json

# AUTHENTICATION IMPORTS
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, SetPasswordForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User

from .models import Employee, Attendance, MonthlySalary, UserProfile
from .forms import EmployeeForm, UserCreateForm, UserEditForm


# ============ PERMISSION DECORATORS ============

def admin_only_required(function=None):
    """Faqat adminlar uchun (superuser, is_staff yoki user_type='admin')"""
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and (
            u.is_superuser or 
            u.is_staff or 
            (hasattr(u, 'profile') and u.profile.user_type == 'admin')
        ),
        login_url='login'
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def admin_or_hr_required(function=None):
    """Faqat admin yoki HR uchun"""
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and (
            u.is_superuser or 
            u.is_staff or 
            (hasattr(u, 'profile') and u.profile.user_type in ['admin', 'hr'])
        ),
        login_url='login'
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def employee_only_required(function=None):
    """Faqat oddiy xodimlar uchun (employee user_type)"""
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and (
            not u.is_superuser and 
            not u.is_staff and 
            (hasattr(u, 'profile') and u.profile.user_type == 'employee')
        ),
        login_url='login'
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


# ============ AUTHENTICATION VIEWS ============

def login_view(request):
    """Login sahifasi"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Xush kelibsiz, {user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Login yoki parol notoʻgʻri!')
    else:
        form = AuthenticationForm()
    
    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    """Logout funksiyasi"""
    logout(request)
    messages.info(request, 'Siz tizimdan chiqdingiz!')
    return redirect('login')


@login_required
def profile_view(request):
    """User profilini ko'rish"""
    user = request.user
    
    # Agar profile bo'lmasa yaratish
    if not hasattr(user, 'profile'):
        UserProfile.objects.create(user=user, user_type='employee')
    
    if request.method == 'POST':
        # Asosiy ma'lumotlar
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        
        # Profil ma'lumotlari
        profile = user.profile
        profile.phone = request.POST.get('phone', profile.phone)
        profile.department = request.POST.get('department', profile.department)
        profile.save()
        
        messages.success(request, 'Profil ma\'lumotlari yangilandi!')
        return redirect('profile')
    
    return render(request, 'auth/profile.html', {
        'user': user,
        'profile': user.profile,
    })


# ============ ADMIN DASHBOARD (faqat adminlar) ============

@login_required
@admin_only_required
def admin_dashboard(request):
    """Admin dashboard - faqat adminlar uchun"""
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    total_employees = Employee.objects.filter(is_active=True).count()
    
    # Adminlar soni
    admin_count = User.objects.filter(
        Q(is_superuser=True) | 
        Q(is_staff=True) |
        Q(profile__user_type='admin')
    ).distinct().count()
    
    # So'nggi foydalanuvchilar
    recent_users = User.objects.all().order_by('-date_joined')[:10]
    
    context = {
        'total_users': total_users,
        'active_users': active_users,
        'total_employees': total_employees,
        'admin_count': admin_count,
        'recent_users': recent_users,
    }
    return render(request, 'admin/dashboard.html', context)


# ============ USER MANAGEMENT (faqat adminlar) ============

# views.py da user_list funksiyasini yangilang:

# views.py

# views.py

@login_required
@admin_only_required
def user_list(request):
    """Userlar ro'yxati - faqat adminlar uchun"""
    users = User.objects.all().order_by('-date_joined')
    
    # Search funksiyasi
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Filter by user type
    user_type = request.GET.get('type', '')
    if user_type:
        users = users.filter(profile__user_type=user_type)
    
    # Faqat aktiv foydalanuvchilar
    active_only = request.GET.get('active', '')
    if active_only == 'true':
        users = users.filter(is_active=True)
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Statistikalar
    admin_count = users.filter(profile__user_type='admin').count()
    hr_count = users.filter(profile__user_type='hr').count()
    manager_count = users.filter(profile__user_type='manager').count()
    employee_count = users.filter(profile__user_type='employee').count()
    superuser_count = users.filter(is_superuser=True).count()
    active_count = users.filter(is_active=True).count()
    
    context = {
        'users': page_obj,
        'search_query': search_query,
        'user_type': user_type,
        'total_users': users.count(),
        'admin_count': admin_count,
        'hr_count': hr_count,
        'manager_count': manager_count,
        'employee_count': employee_count,
        'superuser_count': superuser_count,
        'active_count': active_count,
        'today': date.today(),
    }
    return render(request, 'admin/user_list.html', context)

@login_required
@admin_only_required
def add_user(request):
    """Yangi user qo'shish - faqat adminlar uchun"""
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'{user.username} foydalanuvchi muvaffaqiyatli yaratildi!')
            return redirect('user_list')
        else:
            messages.error(request, 'Iltimos, xatolarni tuzating!')
    else:
        form = UserCreateForm()
    
    employees = Employee.objects.filter(is_active=True)
    
    return render(request, 'admin/user_form.html', {
        'form': form,
        'employees': employees,
        'title': 'Yangi foydalanuvchi qoʻshish',
        'action': 'add',
    })


@login_required
@admin_only_required
def edit_user(request, user_id):
    """Userni tahrirlash - faqat adminlar uchun"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'{user.username} ma\'lumotlari yangilandi!')
            return redirect('user_list')
        else:
            messages.error(request, 'Iltimos, xatolarni tuzating!')
    else:
        form = UserEditForm(instance=user)
    
    employees = Employee.objects.filter(is_active=True)
    
    return render(request, 'admin/user_form.html', {
        'form': form,
        'user': user,
        'employees': employees,
        'title': 'Foydalanuvchini tahrirlash',
        'action': 'edit',
    })


@csrf_exempt
@login_required
@admin_only_required
def delete_user(request, user_id):
    """Userni o'chirish - faqat adminlar uchun"""
    if request.method == 'POST':
        try:
            user = get_object_or_404(User, id=user_id)
            
            # O'zini o'chirishga yo'l qo'ymaslik
            if user == request.user:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Ozingizni ochira olmaysiz'
                })
            
            username = user.username
            user.delete()
            
            messages.success(request, f'{username} foydalanuvchi ochirildi!')
            return JsonResponse({
                'status': 'success',
                'message': f'{username} foydalanuvchi ochirildi!'
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Faqat POST sorovi'})


@login_required
@admin_only_required
def change_user_password(request, user_id):
    """User parolini o'zgartirish - faqat adminlar uchun"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'{user.username} paroli muvaffaqiyatli ozgartirildi!')
            return redirect('user_list')
        else:
            messages.error(request, 'Parol notoʻgʻri yoki bir xil emas!')
    else:
        form = SetPasswordForm(user)
    
    return render(request, 'admin/change_password.html', {
        'form': form,
        'user': user,
        'title': f'{user.username} parolini ozgartirish',
    })


# ============ ASOSIY SAHIFALAR (barcha foydalanuvchilar) ============

def home(request):
    """Asosiy sahifa - login sahifasiga yo'naltiradi"""
    if request.user.is_authenticated:
        return render(request, 'home.html')
    return redirect('login')


@login_required
def dashboard(request):
    """Dashboard - barcha foydalanuvchilar uchun"""
    today = date.today()

    today_checkins = Attendance.objects.filter(date=today, type='in')
    today_checkouts = Attendance.objects.filter(date=today, type='out')

    present_employees = []
    for checkin in today_checkins:
        if not today_checkouts.filter(employee=checkin.employee).exists():
            present_employees.append(checkin.employee)

    all_employees = Employee.objects.filter(is_active=True)
    late_today = today_checkins.filter(status='late')
    day_off_today = today_checkins.filter(status='day_off')

    current_month = today.month
    current_year = today.year
    monthly_salaries = MonthlySalary.objects.filter(year=current_year, month=current_month)

    total_salary = monthly_salaries.aggregate(total=Sum('net_salary'))['total'] or 0
    total_penalty = monthly_salaries.aggregate(total=Sum('total_penalty'))['total'] or 0

    context = {
        'today_checkins': today_checkins,
        'today_checkouts': today_checkouts,
        'present_employees': present_employees,
        'total_employees': all_employees.count(),
        'present_today': today_checkins.count(),
        'checked_out_today': today_checkouts.count(),
        'still_working': len(present_employees),
        'late_today': late_today.count(),
        'day_off_today': day_off_today.count(),
        'all_employees': all_employees,
        'today': today,
        'total_salary': total_salary,
        'total_penalty': total_penalty,
        'active_count': all_employees.count(),
        'absent_today': all_employees.count() - today_checkins.count(),
    }
    return render(request, 'dashboard.html', context)


# ============ XODIMLAR BOSHQARUVI (admin yoki HR) ============

@login_required
@admin_or_hr_required
def employee_list(request):
    """Xodimlar ro'yxati - admin yoki HR uchun"""
    employees = Employee.objects.all().order_by('first_name', 'last_name')
    today = date.today()

    today_checkins = Attendance.objects.filter(date=today, type='in')
    checked_in_ids = list(today_checkins.values_list('employee_id', flat=True))

    context = {
        'employees': employees,
        'today_checkins': today_checkins,
        'checked_in_ids': checked_in_ids,
        'today_day': today.strftime('%A'),
        'today': today,
    }
    return render(request, 'employee_list.html', context)


@login_required
@admin_or_hr_required
def add_employee(request):
    """Yangi xodim qo'shish - admin yoki HR uchun"""
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            employee = form.save()
            messages.success(request, f'{employee.full_name} muvaffaqiyatli qoshildi!')
            return redirect('employee_list')
    else:
        form = EmployeeForm()

    days = [
        {'code': 'monday', 'name': 'Dushanba'},
        {'code': 'tuesday', 'name': 'Seshanba'},
        {'code': 'wednesday', 'name': 'Chorshanba'},
        {'code': 'thursday', 'name': 'Payshanba'},
        {'code': 'friday', 'name': 'Juma'},
        {'code': 'saturday', 'name': 'Shanba'},
        {'code': 'sunday', 'name': 'Yakshanba'},
    ]

    return render(request, 'employee_form_face.html', {
        'form': form,
        'title': 'Yangi xodim qoshish',
        'days': days,
    })


@login_required
@admin_or_hr_required
def edit_employee(request, id):
    """Xodimni tahrirlash - admin yoki HR uchun"""
    employee = get_object_or_404(Employee, id=id)

    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            employee = form.save()
            messages.success(request, f'{employee.full_name} muvaffaqiyatli yangilandi!')
            return redirect('employee_list')
    else:
        form = EmployeeForm(instance=employee)

    days = [
        {'code': 'monday', 'name': 'Dushanba'},
        {'code': 'tuesday', 'name': 'Seshanba'},
        {'code': 'wednesday', 'name': 'Chorshanba'},
        {'code': 'thursday', 'name': 'Payshanba'},
        {'code': 'friday', 'name': 'Juma'},
        {'code': 'saturday', 'name': 'Shanba'},
        {'code': 'sunday', 'name': 'Yakshanba'},
    ]

    return render(request, 'employee_form_face.html', {
        'form': form,
        'title': 'Xodimni tahrirlash',
        'employee': employee,
        'days': days,
    })


@login_required
@admin_or_hr_required
def employee_detail(request, id):
    """Xodim ma'lumotlari - admin yoki HR uchun"""
    employee = get_object_or_404(Employee, id=id)
    attendances = Attendance.objects.filter(employee=employee).order_by('-date', '-time')[:50]
    salaries = MonthlySalary.objects.filter(employee=employee).order_by('-year', '-month')[:12]
    today_schedule = employee.get_today_schedule()

    context = {
        'employee': employee,
        'attendances': attendances,
        'salaries': salaries,
        'today_schedule': today_schedule,
        'work_days': employee.work_days,
        'work_schedule': employee.work_schedule,
    }
    return render(request, 'employee_detail.html', context)


@csrf_exempt
@login_required
@admin_or_hr_required
def delete_employee(request, id):
    """Xodimni o'chirish - admin yoki HR uchun"""
    if request.method == 'POST':
        try:
            employee = get_object_or_404(Employee, id=id)
            name = employee.full_name
            employee.delete()

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': f'{name} ochirildi!'})
            else:
                messages.success(request, f'{name} ochirildi!')
                return redirect('employee_list')

        except Exception as e:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': str(e)})
            else:
                messages.error(request, str(e))
                return redirect('employee_list')

    return redirect('employee_list')


# ============ FACE RECOGNITION DAVOMAT (barcha foydalanuvchilar) ============

@login_required
def checkin_page(request):
    """Kelish sahifasi - barcha foydalanuvchilar uchun"""
    employees = Employee.objects.filter(is_active=True)
    today = date.today()

    today_checkins = Attendance.objects.filter(date=today, type='in')
    checked_in_today = list(today_checkins.values_list('employee_id', flat=True))

    today_code = today.strftime('%A').lower()

    employees_with_schedule = []
    for emp in employees:
        schedule = emp.get_daily_schedule(today_code)
        employees_with_schedule.append({
            'id': emp.id,
            'full_name': emp.full_name,
            'position': emp.position,
            'photo': emp.photo,
            'monthly_salary': emp.monthly_salary,
            'late_penalty_per_minute': emp.late_penalty_per_minute,
            'allowed_late_minutes': emp.allowed_late_minutes,
            'today_schedule': schedule,
            'is_work_day': schedule['is_work_day']
        })

    context = {
        'employees': employees,
        'employees_with_schedule': employees_with_schedule,
        'today_checkins': today_checkins,
        'checked_in_today': checked_in_today,
        'attendance_type': 'in',
        'page_title': 'Kelish',
        'btn_color': 'success',
        'icon': 'sign-in-alt',
        'today_day': today.strftime('%A'),
    }
    return render(request, 'attendance_face.html', context)


@login_required
def checkout_page(request):
    """Chiqish sahifasi - barcha foydalanuvchilar uchun"""
    employees = Employee.objects.filter(is_active=True)
    today = date.today()

    today_checkins = Attendance.objects.filter(date=today, type='in')
    today_checkouts = Attendance.objects.filter(date=today, type='out')

    checked_out_today = list(today_checkouts.values_list('employee_id', flat=True))

    employees_with_checkin = []
    for emp in employees:
        if today_checkins.filter(employee=emp).exists() and not today_checkouts.filter(employee=emp).exists():
            employees_with_checkin.append(emp)

    context = {
        'employees': employees_with_checkin,
        'today_checkouts': today_checkouts,
        'checked_out_today': checked_out_today,
        'attendance_type': 'out',
        'page_title': 'Chiqish',
        'btn_color': 'danger',
        'icon': 'sign-out-alt',
    }
    return render(request, 'attendance_face.html', context)


# ============ DAVOMAT BELGILASH API (barcha foydalanuvchilar) ============

@csrf_exempt
@login_required
def mark_attendance(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            employee_id = data.get('employee_id')
            attendance_type = data.get('type', 'in')

            employee = get_object_or_404(Employee, id=employee_id)
            today = date.today()
            now_time = datetime.now().time()

            today_attendance = Attendance.objects.filter(
                employee=employee,
                date=today,
                type=attendance_type
            )

            if today_attendance.exists():
                last_record = today_attendance.latest('time')
                return JsonResponse({
                    'status': 'error',
                    'message': f'{employee.full_name} {last_record.type_display.lower()}i allaqachon qayd etilgan ({last_record.time})'
                })

            if attendance_type == 'out':
                checkin_exists = Attendance.objects.filter(
                    employee=employee,
                    date=today,
                    type='in'
                ).exists()

                if not checkin_exists:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'{employee.full_name} hali kelmagan. Avval kelishini belgilang!'
                    })

            late_status = 'ontime'
            late_minutes = 0
            penalty_amount = 0
            is_work_day = True

            if attendance_type == 'in':
                schedule = employee.get_today_schedule()
                is_work_day = schedule['is_work_day']

                if not is_work_day:
                    late_status = 'day_off'
                    message = f"{employee.full_name} kelishi qayd etildi. (Bugun dam olish kuni - ish kuni hisoblanmaydi)"
                else:
                    penalty_amount = employee.check_late_penalty(now_time, today)
                    if penalty_amount > 0:
                        late_status = 'late'
                        scheduled_time = datetime.strptime(schedule['start'], '%H:%M').time()
                        late_minutes_total = (datetime.combine(today, now_time) - datetime.combine(today, scheduled_time)).seconds // 60
                        late_minutes = max(0, late_minutes_total - employee.allowed_late_minutes)
                        message = f"{employee.full_name} kelishi qayd etildi. ({late_minutes} daqiqa kechikdi - Jarima: {penalty_amount:,.0f} so'm)"
                    else:
                        message = f"{employee.full_name} kelishi qayd etildi."
            else:
                message = f"{employee.full_name} chiqishi qayd etildi."

            attendance = Attendance.objects.create(
                employee=employee,
                date=today,
                time=now_time,
                type=attendance_type,
                status=late_status,
                late_minutes=late_minutes,
                penalty_amount=penalty_amount,
                notes=''
            )

            response_data = {
                'status': 'success',
                'message': message,
                'employee_name': employee.full_name,
                'time': attendance.time.strftime('%H:%M'),
                'type': attendance.type,
                'type_display': attendance.type_display,
                'late_status': late_status,
                'is_work_day': is_work_day,
                'penalty_amount': float(penalty_amount),
                'late_minutes': late_minutes
            }

            return JsonResponse(response_data)

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Faqat POST soʻrovi qabul qilinadi'})


# ============ HISOBOTLAR (admin yoki HR) ============

@login_required
@admin_or_hr_required
def attendance_report(request):
    """Davomat hisoboti - admin yoki HR uchun"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    employee_id = request.GET.get('employee_id')
    status = request.GET.get('status')

    attendances = Attendance.objects.all().order_by('-date', '-time')

    if start_date:
        attendances = attendances.filter(date__gte=start_date)
    if end_date:
        attendances = attendances.filter(date__lte=end_date)
    if employee_id:
        attendances = attendances.filter(employee_id=employee_id)
    if status:
        attendances = attendances.filter(status=status)

    paginator = Paginator(attendances, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    employees = Employee.objects.filter(is_active=True)

    context = {
        'attendances': page_obj,
        'employees': employees,
        'start_date': start_date,
        'end_date': end_date,
        'selected_employee': employee_id,
        'selected_status': status,
        'total_count': attendances.count(),
        'ontime_count': attendances.filter(status='ontime').count(),
        'late_count': attendances.filter(status='late').count(),
        'early_count': attendances.filter(status='early').count(),
        'day_off_count': attendances.filter(status='day_off').count(),
    }
    return render(request, 'attendance_report.html', context)


@login_required
@admin_or_hr_required
def daily_attendance_report(request):
    """Kunlik hisobot - admin yoki HR uchun"""
    report_date = request.GET.get('date')
    if report_date:
        report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
    else:
        report_date = date.today()

    employees = Employee.objects.filter(is_active=True)
    total_employees = employees.count()

    attendances = Attendance.objects.filter(date=report_date)
    checkins = attendances.filter(type='in')
    
    # Faqat ish kunlaridagi kelishlarni hisoblaymiz
    present_employees = employees.filter(
        attendances__date=report_date, 
        attendances__type='in',
        attendances__status__in=['ontime', 'late', 'early']
    ).distinct()

    # Ish kunlarida kelmaganlar
    absent_employees = []
    for emp in employees:
        day_code = report_date.strftime('%A').lower()
        schedule = emp.get_daily_schedule(day_code)
        
        if schedule['is_work_day']:
            if not present_employees.filter(id=emp.id).exists():
                absent_employees.append(emp)

    late_count = checkins.filter(status='late').count()
    early_count = checkins.filter(status='early').count()
    day_off_count = checkins.filter(status='day_off').count()
    present_count = present_employees.count()

    context = {
        'report_date': report_date,
        'employees': employees,
        'total_employees': total_employees,
        'checkins': checkins,
        'present_employees': present_employees,
        'absent_employees': absent_employees,
        'present_count': present_count,
        'late_count': late_count,
        'early_count': early_count,
        'absent_count': len(absent_employees),
        'day_off_count': day_off_count,
    }

    return render(request, 'daily_report.html', context)


@login_required
@admin_or_hr_required
def weekly_attendance_report(request):
    """Haftalik hisobot - admin yoki HR uchun"""
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    start_date = request.GET.get('start_date', start_of_week.strftime('%Y-%m-%d'))
    end_date = request.GET.get('end_date', end_of_week.strftime('%Y-%m-%d'))

    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        start_date = start_of_week
        end_date = end_of_week

    all_attendances = Attendance.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date', 'time')

    employees = Employee.objects.filter(is_active=True)
    weekly_stats = []

    for employee in employees:
        employee_attendances = all_attendances.filter(employee=employee)
        
        employee_checkins = employee_attendances.filter(type='in')
        employee_checkouts = employee_attendances.filter(type='out')
        
        present_days = employee_checkins.count()
        
        days_data = {}
        current_date = start_date
        
        while current_date <= end_date:
            day_name = current_date.strftime('%A')
            day_checkin = employee_checkins.filter(date=current_date).first()
            
            if day_checkin:
                day_checkout = employee_checkouts.filter(date=current_date).first()
                
                # Kechikishni soat va daqiqaga ajratish
                late_hours = day_checkin.late_minutes // 60
                late_minutes = day_checkin.late_minutes % 60
                
                days_data[day_name] = {
                    'checkin': day_checkin.time,
                    'checkout': day_checkout.time if day_checkout else None,
                    'status': day_checkin.status,
                    'late_minutes': day_checkin.late_minutes,
                    'late_hours': late_hours,
                    'late_minutes_remainder': late_minutes,
                }
            else:
                days_data[day_name] = None
            
            current_date += timedelta(days=1)

        weekly_stats.append({
            'employee': employee,
            'present_days': present_days,
            'days_data': days_data,
            'late_days': employee_checkins.filter(status='late').count(),
            'early_days': employee_checkins.filter(status='early').count(),
            'early_leave_days': 0,
        })

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'weekly_stats': weekly_stats,
        'total_employees': employees.count(),
    }
    return render(request, 'weekly_report.html', context)


@login_required
@admin_or_hr_required
def monthly_attendance_report(request):
    """Oylik hisobot - admin yoki HR uchun"""
    today = date.today()
    start_of_month = date(today.year, today.month, 1)

    if today.month == 12:
        end_of_month = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        end_of_month = date(today.year, today.month + 1, 1) - timedelta(days=1)

    month = request.GET.get('month', today.month)
    year = request.GET.get('year', today.year)

    try:
        month = int(month)
        year = int(year)
        start_of_month = date(year, month, 1)
        if month == 12:
            end_of_month = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_of_month = date(year, month + 1, 1) - timedelta(days=1)
    except ValueError:
        month = today.month
        year = today.year

    attendances = Attendance.objects.filter(
        date__gte=start_of_month,
        date__lte=end_of_month,
        type='in'
    ).order_by('date', 'time')

    employees = Employee.objects.filter(is_active=True)
    monthly_stats = []

    for employee in employees:
        employee_attendances = attendances.filter(employee=employee)
        present_days = employee_attendances.count()

        work_days_in_month = 0
        current_date = start_of_month
        while current_date <= end_of_month:
            if current_date.strftime('%A').lower() in employee.work_days:
                work_days_in_month += 1
            current_date += timedelta(days=1)

        monthly_stats.append({
            'employee': employee,
            'present_days': present_days,
            'work_days': work_days_in_month,
            'absent_days': max(0, work_days_in_month - present_days),
            'late_days': employee_attendances.filter(status='late').count(),
            'early_days': employee_attendances.filter(status='early').count(),
            'day_off_days': employee_attendances.filter(status='day_off').count(),
            'attendance_rate': (present_days / work_days_in_month * 100) if work_days_in_month > 0 else 0,
        })

    months_list = [
        (1, 'Yanvar'), (2, 'Fevral'), (3, 'Mart'), (4, 'Aprel'),
        (5, 'May'), (6, 'Iyun'), (7, 'Iyul'), (8, 'Avgust'),
        (9, 'Sentabr'), (10, 'Oktabr'), (11, 'Noyabr'), (12, 'Dekabr'),
    ]

    current_year = date.today().year
    years = range(current_year - 5, current_year + 1)

    context = {
        'month': month,
        'year': year,
        'start_date': start_of_month,
        'end_date': end_of_month,
        'monthly_stats': monthly_stats,
        'months': months_list,
        'years': years,
        'total_employees': employees.count(),
    }
    return render(request, 'monthly_report.html', context)


@login_required
@admin_or_hr_required
def salary_report(request):
    """Maosh hisoboti - admin yoki HR uchun"""
    today = date.today()
    selected_year = int(request.GET.get('year', today.year))
    selected_month = int(request.GET.get('month', today.month))
    selected_employee = request.GET.get('employee_id')
    
    # Yillar va oylar
    years = list(range(today.year - 5, today.year + 1))
    years.reverse()
    
    months = [
        (1, 'Yanvar'), (2, 'Fevral'), (3, 'Mart'), (4, 'Aprel'),
        (5, 'May'), (6, 'Iyun'), (7, 'Iyul'), (8, 'Avgust'),
        (9, 'Sentabr'), (10, 'Oktabr'), (11, 'Noyabr'), (12, 'Dekabr')
    ]
    
    # Xodimlar
    employees = Employee.objects.filter(is_active=True)
    
    if selected_employee:
        employees = employees.filter(id=selected_employee)
    
    salaries = []
    total_salary = 0
    total_penalty = 0
    paid_count = 0
    unpaid_count = 0
    day_off_count = 0
    total_work_days = 0
    total_present_days = 0
    total_absent_days = 0
    total_late_days = 0
    
    # Majburiy hisoblash
    force_calculate = request.GET.get('calculate') in ['true', 'force']
    
    for employee in employees:
        try:
            # Maosh yozuvini olish yoki yaratish
            salary, created = MonthlySalary.objects.get_or_create(
                employee=employee,
                year=selected_year,
                month=selected_month,
                defaults={
                    'basic_salary': employee.monthly_salary or 0,
                    'is_paid': False
                }
            )
            
            # Hisoblash
            if force_calculate or created:
                salary.calculate_salary()
                salary.save()
            elif salary.present_days == 0 and salary.work_days > 0:
                # Agar kelgan kunlar 0 bo'lsa, lekin ish kunlari bor bo'lsa, hisoblaymiz
                salary.calculate_salary()
                salary.save()
            
            salaries.append(salary)
            
            # Umumiy statistikalar
            total_salary += salary.net_salary or 0
            total_penalty += salary.total_penalty or 0
            total_work_days += salary.work_days or 0
            total_present_days += salary.present_days or 0
            total_absent_days += salary.absent_days or 0
            total_late_days += salary.late_days or 0
            day_off_count += salary.day_off_days or 0
            
            if salary.is_paid:
                paid_count += 1
            else:
                unpaid_count += 1
                
        except Exception as e:
            print(f"Xato: {employee.full_name} uchun maosh hisoblashda xatolik: {e}")
            continue
    
    # Kontekst
    context = {
        'salaries': salaries,
        'employees': Employee.objects.filter(is_active=True),
        'years': years,
        'months': months,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'selected_employee': int(selected_employee) if selected_employee else '',
        'total_salary': total_salary,
        'total_penalty': total_penalty,
        'paid_count': paid_count,
        'unpaid_count': unpaid_count,
        'day_off_count': day_off_count,
        'total_work_days': total_work_days,
        'total_present_days': total_present_days,
        'total_absent_days': total_absent_days,
        'total_late_days': total_late_days,
    }
    
    return render(request, 'salary_report.html', context)


@login_required
@admin_or_hr_required
def calculate_monthly_salary(request, employee_id, year, month):
    """Maosh hisoblash - admin yoki HR uchun"""
    employee = get_object_or_404(Employee, id=employee_id)

    salary, created = MonthlySalary.objects.get_or_create(
        employee=employee,
        year=year,
        month=month,
        defaults={'basic_salary': employee.monthly_salary}
    )

    net_salary = salary.calculate_salary()

    return JsonResponse({
        'status': 'success',
        'message': f'{employee.full_name} uchun {month}/{year} oyi maoshi hisoblandi',
        'net_salary': float(net_salary),
        'basic_salary': float(salary.basic_salary),
        'total_penalty': float(salary.total_penalty),
        'present_days': salary.present_days,
        'late_days': salary.late_days,
        'absent_days': salary.absent_days,
        'day_off_days': salary.day_off_days,
    })


@csrf_exempt
@login_required
@admin_or_hr_required
def mark_salary_paid(request, salary_id):
    """Maosh to'landi deb belgilash - admin yoki HR uchun"""
    salary = get_object_or_404(MonthlySalary, id=salary_id)

    if request.method == 'POST':
        salary.is_paid = True
        salary.paid_date = date.today()
        salary.save()

        return JsonResponse({
            'status': 'success',
            'message': f'{salary.employee.full_name} uchun {salary.month}/{salary.year} oyi maoshi tolandi deb belgilandi'
        })

    return JsonResponse({'status': 'error', 'message': 'Faqat POST soʻrovi'})


# ============ QO'SHIMCHA API (barcha foydalanuvchilar) ============

@login_required
def get_employee_schedule(request, employee_id):
    """Xodim jadvali - barcha foydalanuvchilar uchun"""
    employee = get_object_or_404(Employee, id=employee_id)

    today_schedule = employee.get_today_schedule()
    weekly_schedule = {}

    for day_code, day_name in Employee.WORK_DAYS_CHOICES:
        schedule = employee.get_daily_schedule(day_code)
        weekly_schedule[day_code] = {
            'name': day_name,
            'start': schedule['start'],
            'end': schedule['end'],
            'is_work_day': schedule['is_work_day'],
        }

    return JsonResponse({
        'status': 'success',
        'employee_name': employee.full_name,
        'today_schedule': today_schedule,
        'weekly_schedule': weekly_schedule,
    })


@login_required
def get_today_attendance(request):
    """Bugungi davomat - barcha foydalanuvchilar uchun"""
    today = date.today()

    checkins = Attendance.objects.filter(date=today, type='in')
    checkouts = Attendance.objects.filter(date=today, type='out')

    checkins_list = [{
        'id': att.id,
        'employee_name': att.employee.full_name,
        'time': att.time.strftime('%H:%M'),
        'status': att.status,
        'late_minutes': att.late_minutes,
        'penalty_amount': float(att.penalty_amount),
    } for att in checkins]

    checkouts_list = [{
        'id': att.id,
        'employee_name': att.employee.full_name,
        'time': att.time.strftime('%H:%M'),
    } for att in checkouts]

    return JsonResponse({
        'status': 'success',
        'date': today.strftime('%Y-%m-%d'),
        'checkins': checkins_list,
        'checkouts': checkouts_list,
        'total_checkins': len(checkins_list),
        'total_checkouts': len(checkouts_list),
    })