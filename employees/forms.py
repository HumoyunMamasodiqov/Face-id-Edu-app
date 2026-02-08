from django import forms
from .models import Employee
from datetime import time
import json
# forms.py

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Employee, UserProfile

class UserCreateForm(UserCreationForm):
    """Yangi foydalanuvchi yaratish formasi"""
    user_type = forms.ChoiceField(
        choices=UserProfile.USER_TYPES,
        label='Foydalanuvchi turi',
        initial='employee'
    )
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True),
        required=False,
        label='Xodim bilan bog‘lash',
        empty_label="Xodim tanlanmagan"
    )
    phone = forms.CharField(max_length=20, required=False, label='Telefon')
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 
                  'password1', 'password2', 'is_active', 'is_staff']
        labels = {
            'username': 'Login',
            'is_active': 'Faol',
            'is_staff': 'Admin huquqi',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Parol maydonlarini yaxshilash
        self.fields['password1'].help_text = "Kamida 8 belgidan iborat boʻlishi kerak"
        self.fields['password2'].help_text = "Yugoridagi parolni tasdiqlang"
    
    def save(self, commit=True):
        """User va uning profilini bir vaqtda yaratish"""
        # Avval user yaratish
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            
            # UserProfile yaratish
            # get_or_create bilan profil borligini tekshirish
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'user_type': self.cleaned_data.get('user_type', 'employee'),
                    'employee': self.cleaned_data.get('employee'),
                    'phone': self.cleaned_data.get('phone', '')
                }
            )
            
            # Agar profil allaqachon mavjud bo'lsa, yangilash
            if not created:
                profile.user_type = self.cleaned_data.get('user_type', 'employee')
                profile.employee = self.cleaned_data.get('employee')
                profile.phone = self.cleaned_data.get('phone', '')
                profile.save()
        
        return user

class UserEditForm(forms.ModelForm):
    """Foydalanuvchini tahrirlash formasi"""
    user_type = forms.ChoiceField(
        choices=UserProfile.USER_TYPES,
        label='Foydalanuvchi turi'
    )
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True),
        required=False,
        label='Xodim bilan bog‘lash',
        empty_label="Xodim tanlanmagan"
    )
    phone = forms.CharField(max_length=20, required=False, label='Telefon')
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 
                  'is_active', 'is_staff']
        labels = {
            'username': 'Login',
            'is_active': 'Faol',
            'is_staff': 'Admin huquqi',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            try:
                profile = self.instance.profile
                self.fields['user_type'].initial = profile.user_type
                self.fields['employee'].initial = profile.employee
                self.fields['phone'].initial = profile.phone
            except UserProfile.DoesNotExist:
                pass
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        if commit:
            user.save()
            # UserProfile yangilash
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.user_type = self.cleaned_data['user_type']
            profile.employee = self.cleaned_data['employee']
            profile.phone = self.cleaned_data['phone']
            profile.save()
        
        return user

class EmployeeForm(forms.ModelForm):
    """Xodim formasi"""
    class Meta:
        model = Employee
        fields = '__all__'
        widgets = {
            'work_days': forms.CheckboxSelectMultiple(choices=Employee.WORK_DAYS_CHOICES),
            'work_schedule': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ism va familiya maydonlarini majburiy qilish
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True 
class EmployeeForm(forms.ModelForm):
    # Ish kunlari uchun checkboxlar
    monday = forms.BooleanField(required=False, label='Dushanba')
    tuesday = forms.BooleanField(required=False, label='Seshanba')
    wednesday = forms.BooleanField(required=False, label='Chorshanba')
    thursday = forms.BooleanField(required=False, label='Payshanba')
    friday = forms.BooleanField(required=False, label='Juma')
    saturday = forms.BooleanField(required=False, label='Shanba')
    sunday = forms.BooleanField(required=False, label='Yakshanba')
    
    # Har kun uchun vaqt maydonlari
    for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
        locals()[f'start_time_{day}'] = forms.TimeField(
            required=False,
            widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            initial='09:00'
        )
        locals()[f'end_time_{day}'] = forms.TimeField(
            required=False,
            widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            initial='18:00'
        )
    
    # Maosh va jarima maydonlari
    monthly_salary = forms.DecimalField(
        label='Oylik maosh (soʻmda)',
        min_value=0,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Masalan: 5000000'
        })
    )
    
    late_penalty_per_minute = forms.DecimalField(
        label='Har bir daqiqa uchun jarima (soʻm)',
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Masalan: 1000'
        })
    )
    
    allowed_late_minutes = forms.IntegerField(
        label='Ruxsat etilgan kechikish (daqiqa)',
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Masalan: 10'
        })
    )
    
    daily_work_hours = forms.DecimalField(
        label='Kunlik ish soatlari',
        min_value=0,
        max_value=24,
        max_digits=4,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Masalan: 8.0'
        })
    )
    
    class Meta:
        model = Employee
        fields = [
            'first_name', 'last_name', 'position', 'department',
            'phone', 'email', 'photo', 'monthly_salary', 
            'late_penalty_per_minute', 'allowed_late_minutes',
            'daily_work_hours', 'is_active'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ism'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Familya'}),
            'position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lavozim'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Bo\'lim'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Telefon'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Mavjud xodimni tahrirlashda checkboxlarni belgilash
        if self.instance and self.instance.pk:
            work_days = self.instance.work_days or []
            self.fields['monday'].initial = 'monday' in work_days
            self.fields['tuesday'].initial = 'tuesday' in work_days
            self.fields['wednesday'].initial = 'wednesday' in work_days
            self.fields['thursday'].initial = 'thursday' in work_days
            self.fields['friday'].initial = 'friday' in work_days
            self.fields['saturday'].initial = 'saturday' in work_days
            self.fields['sunday'].initial = 'sunday' in work_days
            
            # Ish jadvalini yuklash
            schedule = self.instance.work_schedule or {}
            for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
                if day in schedule:
                    self.fields[f'start_time_{day}'].initial = schedule[day].get('start', '09:00')
                    self.fields[f'end_time_{day}'].initial = schedule[day].get('end', '18:00')
    
    def get_day_name(self, day_code):
        day_names = {
            'monday': 'Dushanba',
            'tuesday': 'Seshanba',
            'wednesday': 'Chorshanba',
            'thursday': 'Payshanba',
            'friday': 'Juma',
            'saturday': 'Shanba',
            'sunday': 'Yakshanba'
        }
        return day_names.get(day_code, day_code)
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Ish kunlarini to'plash
        work_days = []
        work_schedule = {}
        
        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            day_checkbox = cleaned_data.get(f'{day}')
            
            if day_checkbox:  # Agar bu kun tanlangan bo'lsa
                work_days.append(day)
                
                start_time = cleaned_data.get(f'start_time_{day}')
                end_time = cleaned_data.get(f'end_time_{day}')
                
                # Agar vaqt kiritilmagan bo'lsa, default qo'yish
                if not start_time:
                    start_time = time(9, 0)
                if not end_time:
                    end_time = time(18, 0)
                
                # Vaqtni tekshirish
                if start_time and end_time and start_time >= end_time:
                    day_name = self.get_day_name(day)
                    raise forms.ValidationError(f"{day_name} uchun ish boshlash vaqti tugash vaqtidan oldin bo'lishi kerak!")
                
                work_schedule[day] = {
                    'start': start_time.strftime('%H:%M'),
                    'end': end_time.strftime('%H:%M')
                }
        
        if not work_days:
            raise forms.ValidationError("Kamida bitta ish kunini tanlang!")
        
        cleaned_data['work_days'] = work_days
        cleaned_data['work_schedule'] = work_schedule
        
        # Kunlik ish soatlarini avtomatik hisoblash (agar kiritilmagan bo'lsa)
        if not cleaned_data.get('daily_work_hours'):
            # Birinchi ish kunining ish soatlarini hisoblash
            first_day = work_days[0] if work_days else 'monday'
            schedule = work_schedule.get(first_day, {'start': '09:00', 'end': '18:00'})
            
            start_str = schedule['start']
            end_str = schedule['end']
            
            start_time = datetime.strptime(start_str, '%H:%M').time()
            end_time = datetime.strptime(end_str, '%H:%M').time()
            
            start_dt = datetime.combine(date.today(), start_time)
            end_dt = datetime.combine(date.today(), end_time)
            
            # Tushlik vaqtini chiqarib (1 soat)
            diff_hours = (end_dt - start_dt).seconds / 3600 - 1
            cleaned_data['daily_work_hours'] = max(0, diff_hours)
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.work_days = self.cleaned_data['work_days']
        instance.work_schedule = self.cleaned_data['work_schedule']
        
        if commit:
            instance.save()
        return instance


from datetime import datetime, date