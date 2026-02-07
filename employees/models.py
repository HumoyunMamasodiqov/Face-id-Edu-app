from django.db import models
from django.utils import timezone
from datetime import datetime, date, time, timedelta
import calendar


# models.py faylida:

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Har yangi user yaratilganda avtomatik profile yaratish"""
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """User saqlanganda profile ni saqlash"""
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)

# models.py fayliga qo'shing:

from django.contrib.auth.models import User
from django.db import models

class UserProfile(models.Model):
    """Foydalanuvchi profili"""
    USER_TYPES = [
        ('admin', 'Administrator'),
        ('hr', 'HR Manager'),
        ('manager', 'Department Manager'),
        ('employee', 'Employee'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='employee')
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100, blank=True)
    employee = models.ForeignKey('Employee', on_delete=models.SET_NULL, null=True, blank=True, 
                                 related_name='user_profile')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Foydalanuvchi profili'
        verbose_name_plural = 'Foydalanuvchi profillari'
    
    def __str__(self):
        return f"{self.user.username} - {self.get_user_type_display()}"
    
    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}"

class Employee(models.Model):
    WORK_DAYS_CHOICES = [
        ('monday', 'Dushanba'),
        ('tuesday', 'Seshanba'),
        ('wednesday', 'Chorshanba'),
        ('thursday', 'Payshanba'),
        ('friday', 'Juma'),
        ('saturday', 'Shanba'),
        ('sunday', 'Yakshanba'),
    ]

    first_name = models.CharField(max_length=100, verbose_name='Ismi')
    last_name = models.CharField(max_length=100, verbose_name='Familyasi')
    position = models.CharField(max_length=100, verbose_name='Lavozimi')
    department = models.CharField(max_length=100, verbose_name="Bo'lim")
    phone = models.CharField(max_length=20, blank=True, verbose_name='Telefon')
    email = models.EmailField(blank=True, verbose_name='Email')
    photo = models.ImageField(upload_to='employee_photos/', verbose_name='Rasm')

    # Ish kunlari (masalan: ['monday', 'tuesday', ...])
    work_days = models.JSONField(default=list, verbose_name='Ish kunlari')

    # Har bir kun uchun ish jadvali
    # {"monday": {"start": "09:00", "end": "18:00"}, ...}
    work_schedule = models.JSONField(default=dict, verbose_name='Ish jadvali')

    monthly_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name='Oylik maosh'
    )

    late_penalty_per_minute = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1000,
        verbose_name='Har daqiqa uchun jarima'
    )

    allowed_late_minutes = models.IntegerField(
        default=10,
        verbose_name='Ruxsat etilgan kechikish (daq.)'
    )

    daily_work_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=8.0,
        verbose_name='Kunlik ish soatlari'
    )

    is_active = models.BooleanField(default=True, verbose_name='Faol')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan sana')

    class Meta:
        ordering = ['first_name', 'last_name']
        verbose_name = 'Xodim'
        verbose_name_plural = 'Xodimlar'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def work_days_display(self):
        day_mapping = dict(self.WORK_DAYS_CHOICES)
        return ", ".join([day_mapping.get(day, day) for day in self.work_days])

    def get_daily_schedule(self, day_code):
        schedule = self.work_schedule.get(day_code, {})
        return {
            'start': schedule.get('start', '09:00'),
            'end': schedule.get('end', '18:00'),
            'is_work_day': day_code in self.work_days
        }

    def get_today_schedule(self):
        today_code = datetime.now().strftime('%A').lower()
        return self.get_daily_schedule(today_code)

    def calculate_daily_salary(self, year=None, month=None):
        if not self.monthly_salary or not self.work_days:
            return 0

        if not year or not month:
            today = date.today()
            year = today.year
            month = today.month

        days_in_month = calendar.monthrange(year, month)[1]
        work_days_count = 0

        for day in range(1, days_in_month + 1):
            current_date = date(year, month, day)
            if current_date.strftime('%A').lower() in self.work_days:
                work_days_count += 1

        if work_days_count == 0:
            return 0

        return self.monthly_salary / work_days_count

    def check_late_penalty(self, check_in_time, check_date=None):
        if not check_in_time:
            return 0

        if check_date is None:
            check_date = date.today()

        day_code = check_date.strftime('%A').lower()
        schedule = self.get_daily_schedule(day_code)

        if not schedule['is_work_day']:
            return 0

        scheduled_time = datetime.strptime(schedule['start'], '%H:%M').time()
        scheduled_dt = datetime.combine(check_date, scheduled_time)
        actual_dt = datetime.combine(check_date, check_in_time)

        if actual_dt > scheduled_dt:
            late_minutes_total = (actual_dt - scheduled_dt).seconds // 60
            effective_late_minutes = max(0, late_minutes_total - self.allowed_late_minutes)
            return effective_late_minutes * self.late_penalty_per_minute

        return 0


class Attendance(models.Model):
    ATTENDANCE_TYPES = [
        ('in', 'Kelish'),
        ('out', 'Chiqish'),
    ]

    STATUS_CHOICES = [
        ('ontime', 'Vaqtida'),
        ('late', 'Kechikdi'),
        ('early', 'Erta keldi'),
        ('absent', "Kelmagan"),
        ('day_off', 'Dam olish'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    time = models.TimeField()
    type = models.CharField(max_length=3, choices=ATTENDANCE_TYPES, default='in')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ontime')
    late_minutes = models.IntegerField(default=0)
    penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-time']
        unique_together = ['employee', 'date', 'type']
        verbose_name = 'Davomat'
        verbose_name_plural = 'Davomatlar'

    def __str__(self):
        type_text = "Kelish" if self.type == 'in' else "Chiqish"
        return f"{self.employee.full_name} - {self.date} {self.time} ({type_text})"

    @property
    def type_display(self):
        return "Kelish" if self.type == 'in' else "Chiqish"
# models.py - Attendance modelida

    def calculate_late_status(self):
        if self.type != 'in' or not self.time:
            return self.status

        check_date = self.date
        check_in_time = self.time

        day_code = check_date.strftime('%A').lower()
        schedule = self.employee.get_daily_schedule(day_code)

        # 🔥 Yangi qo'shilgan qism
        if not schedule['is_work_day']:
            self.status = 'day_off'
            self.late_minutes = 0
            self.penalty_amount = 0
            self.save()
            return self.status  # Ish kuni emas deb belgilash

        # Ish kuni bo'lsa, oddiy hisoblash
        scheduled_time = datetime.strptime(schedule['start'], '%H:%M').time()
        scheduled_dt = datetime.combine(check_date, scheduled_time)
        actual_dt = datetime.combine(check_date, check_in_time)

        if actual_dt > scheduled_dt:
            late_minutes_total = (actual_dt - scheduled_dt).seconds // 60
            self.late_minutes = max(0, late_minutes_total - self.employee.allowed_late_minutes)

            if self.late_minutes > 0:
                self.status = 'late'
                self.penalty_amount = self.late_minutes * self.employee.late_penalty_per_minute
            else:
                self.status = 'ontime'
                self.penalty_amount = 0
        elif actual_dt < scheduled_dt:
            self.status = 'early'
            self.late_minutes = 0
            self.penalty_amount = 0
        else:
            self.status = 'ontime'
            self.late_minutes = 0
            self.penalty_amount = 0

        self.save()
        return self.status
# models.py - MonthlySalary modeli

class MonthlySalary(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='salaries')
    year = models.IntegerField()
    month = models.IntegerField()

    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_penalty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    work_days = models.IntegerField(default=0)
    present_days = models.IntegerField(default=0)
    late_days = models.IntegerField(default=0)
    absent_days = models.IntegerField(default=0)
    day_off_days = models.IntegerField(default=0)

    notes = models.TextField(blank=True)
    is_paid = models.BooleanField(default=False)
    paid_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-year', '-month']
        unique_together = ['employee', 'year', 'month']
        verbose_name = 'Oylik maosh'
        verbose_name_plural = 'Oylik maoshlar'

    def __str__(self):
        month_names = [
            '', 'Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun',
            'Iyul', 'Avgust', 'Sentabr', 'Oktabr', 'Noyabr', 'Dekabr'
        ]
        return f"{self.employee.full_name} - {month_names[self.month]} {self.year}"

    def get_month_display(self):
        month_names = {
            1: 'Yanvar', 2: 'Fevral', 3: 'Mart', 4: 'Aprel',
            5: 'May', 6: 'Iyun', 7: 'Iyul', 8: 'Avgust',
            9: 'Sentabr', 10: 'Oktabr', 11: 'Noyabr', 12: 'Dekabr'
        }
        return month_names.get(self.month, str(self.month))

    def calculate_salary(self):
        # Asosiy maosh
        self.basic_salary = self.employee.monthly_salary or 0
        
        # Oyning boshlanishi va oxiri
        start_date = date(self.year, self.month, 1)
        if self.month == 12:
            end_date = date(self.year + 1, 1, 1)
        else:
            end_date = date(self.year, self.month + 1, 1)
        
        # Barcha kelishlar
        attendances = Attendance.objects.filter(
            employee=self.employee,
            date__gte=start_date,
            date__lt=end_date,
            type='in'
        )
        
        # Ish kunlari soni (xodimning ish jadvalidan)
        self.work_days = 0
        current_date = start_date
        while current_date < end_date:
            day_code = current_date.strftime('%A').lower()
            if day_code in self.employee.work_days:
                self.work_days += 1
            current_date += timedelta(days=1)
        
        # Kelgan kunlar (faqat ish kunlari)
        work_day_attendances = attendances.exclude(status='day_off')
        day_off_attendances = attendances.filter(status='day_off')
        
        # Ish kunlaridagi kelishlar
        self.present_days = work_day_attendances.count()
        
        # Kechikishlar
        self.late_days = work_day_attendances.filter(status='late').count()
        
        # Dam olish kunlari kelganlar
        self.day_off_days = day_off_attendances.count()
        
        # Kelmagan kunlar
        self.absent_days = max(0, self.work_days - self.present_days)
        
        # Jarimalar (faqat ish kunlari uchun)
        self.total_penalty = work_day_attendances.filter(status='late').aggregate(
            total=models.Sum('penalty_amount')
        )['total'] or 0
        
        # Kunlik maosh
        if self.work_days > 0:
            daily_salary = self.basic_salary / self.work_days
        else:
            daily_salary = 0
        
        # Kelmaganlik uchun jarima
        absent_penalty = self.absent_days * daily_salary
        
        # Sof maosh
        self.net_salary = max(0, self.basic_salary - self.total_penalty - absent_penalty + self.total_bonus)
        
        self.save()
        return self.net_salary


def calculate_salary(self):
    """
    Sof maoshni to'g'ri hisoblash:
    Sof maosh = Asosiy maosh - Jarimalar - Kelmaganlik jarimasi + Mukofotlar
    """
    try:
        print(f"\n=== {self.employee.full_name} uchun maosh hisoblash ({self.month}/{self.year}) ===")
        
        # 1. ASOSIY MAOSH
        self.basic_salary = self.employee.monthly_salary or 0
        print(f"1. Asosiy maosh: {self.basic_salary} so'm")
        
        # 2. OY ORALIG'I
        start_date = date(self.year, self.month, 1)
        if self.month == 12:
            end_date = date(self.year + 1, 1, 1)
        else:
            end_date = date(self.year, self.month + 1, 1)
        
        # 3. DAVOMATLARNI OLISH
        attendances = Attendance.objects.filter(
            employee=self.employee,
            date__gte=start_date,
            date__lt=end_date,
            type='in'
        ).order_by('date')
        
        # 4. ISH KUNLARI SONI
        self.work_days = 0
        work_dates = []
        current_date = start_date
        while current_date < end_date:
            day_code = current_date.strftime('%A').lower()
            if day_code in self.employee.work_days:
                self.work_days += 1
                work_dates.append(current_date)
            current_date += timedelta(days=1)
        
        print(f"2. Ish kunlari soni: {self.work_days} kun")
        
        # 5. KELGAN KUNLARNI HISOBLASH
        work_day_attendance_dates = []
        day_off_attendance_dates = []
        
        for attendance in attendances:
            day_code = attendance.date.strftime('%A').lower()
            schedule = self.employee.get_daily_schedule(day_code)
            
            if schedule['is_work_day']:
                # ISH KUNI
                if attendance.status != 'day_off':
                    work_day_attendance_dates.append(attendance.date)
                else:
                    day_off_attendance_dates.append(attendance.date)
            else:
                # DAM OLISH KUNI
                day_off_attendance_dates.append(attendance.date)
        
        # Noyob sanalarni hisoblash (bir kunda bir marta kelgan deb)
        self.present_days = len(set(work_day_attendance_dates))
        self.day_off_days = len(set(day_off_attendance_dates))
        
        # Kechikishlar
        self.late_days = attendances.filter(
            date__in=work_day_attendance_dates,
            status='late'
        ).count()
        
        # Kelmagan kunlar
        self.absent_days = max(0, self.work_days - self.present_days)
        
        print(f"3. Ish kuni kelgan: {self.present_days} kun")
        print(f"4. Kechikkan kunlar: {self.late_days} kun")
        print(f"5. Dam olish kuni kelgan: {self.day_off_days} kun")
        print(f"6. Kelmagan kunlar: {self.absent_days} kun")
        
        # 6. JARIMALARNI HISOBLASH
        # a) Kechikish jarimalari
        late_penalty = attendances.filter(
            date__in=work_day_attendance_dates,
            status='late'
        ).aggregate(total=Sum('penalty_amount'))['total'] or 0
        
        # b) Kunlik maoshni hisoblash
        if self.work_days > 0:
            daily_salary = self.basic_salary / self.work_days
        else:
            daily_salary = 0
        
        # c) Kelmaganlik jarimasi
        absent_penalty = self.absent_days * daily_salary
        
        # d) Jami jarima
        self.total_penalty = late_penalty + absent_penalty
        
        print(f"7. Kunlik maosh: {daily_salary:.2f} so'm")
        print(f"8. Kechikish jarimasi: {late_penalty} so'm")
        print(f"9. Kelmaganlik jarimasi: {absent_penalty:.2f} so'm")
        print(f"10. Jami jarima: {self.total_penalty:.2f} so'm")
        
        # 7. SOF MAOSHNI HISOBLASH (ASOSIY FORMULA)
        # Sof maosh = Asosiy maosh - Jami jarima + Mukofotlar
        self.net_salary = self.basic_salary - self.total_penalty + self.total_bonus
        
        # Sof maosh manfiy bo'lmasligi kerak
        if self.net_salary < 0:
            self.net_salary = 0
        
        print(f"11. Mukofotlar: {self.total_bonus} so'm")
        print(f"12. SOF MAOSH ({self.basic_salary} - {self.total_penalty} + {self.total_bonus}): {self.net_salary:.2f} so'm")
        
        # 8. SAQLASH
        self.save()
        print(f"=== Hisoblash yakunlandi ===\n")
        
        return self.net_salary
        
    except Exception as e:
        print(f"XATO: Maosh hisoblashda xatolik - {str(e)}")
        # Agar xato bo'lsa, standart qiymatlarni qo'yamiz
        self.basic_salary = self.employee.monthly_salary or 0
        self.total_penalty = 0
        self.net_salary = self.basic_salary
        self.save()
        return self.net_salary