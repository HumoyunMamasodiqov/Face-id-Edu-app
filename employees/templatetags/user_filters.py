# employees/templatetags/user_filters.py

from django import template

register = template.Library()

@register.filter
def filter_by_user_type(users, user_type):
    """Foydalanuvchilarni user_type bo'yicha filtrlaydi"""
    return users.filter(profile__user_type=user_type)

@register.filter
def get_user_role(user):
    """Foydalanuvchi rolini qaytaradi"""
    if hasattr(user, 'profile'):
        return user.profile.get_user_type_display()
    return 'Xodim'

@register.filter
def is_admin(user):
    """Foydalanuvchi admin ekanligini tekshiradi"""
    return user.is_superuser or user.is_staff or (hasattr(user, 'profile') and user.profile.user_type == 'admin')

@register.filter
def is_active_badge(user):
    """Foydalanuvchi holati uchun badge"""
    if user.is_active:
        return '<span class="badge bg-success"><i class="fas fa-check-circle me-1"></i> Faol</span>'
    else:
        return '<span class="badge bg-danger"><i class="fas fa-times-circle me-1"></i> Nofaol</span>'

@register.filter(name='safe_html')
def safe_html(value):
    """HTML ni xavfsiz qaytaradi"""
    return template.utils.safedata.SafeString(value)