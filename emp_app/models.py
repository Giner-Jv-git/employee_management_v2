from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import RegexValidator

class EmployeeProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('hr', 'HR Personnel'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone_number = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

class EmployeeData(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    # Phone number validator (09XXXXXXXXX format)
    phone_regex = RegexValidator(
        regex=r'^09\d{9}$',
        message="Phone number must be 11 digits starting with 09 (e.g. 09123456789)"
    )
    
    POSITION_CHOICES = [
        ('front_desk', 'Front Desk / Receptionist'),
        ('housekeeping', 'Housekeeping Staff'),
        ('chef', 'Chef / Kitchen Staff'),
        ('waitstaff', 'Waitstaff / Servers'),
        ('maintenance', 'Maintenance / Engineering Staff'),
        ('lifeguard', 'Lifeguard'),
        ('security', 'Security Personnel'),
        ('event_coordinator', 'Event Coordinator / Banquet Staff'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    name = models.CharField(max_length=100)
    employee_id = models.CharField(max_length=20, unique=True)
    profile_picture = models.ImageField(upload_to='employee_profiles/', blank=True, null=True, help_text='Upload a profile picture (recommended size: 300x300px)')
    age = models.PositiveIntegerField()
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    address = models.TextField()
    phone_number = models.CharField(
        max_length=11, 
        validators=[phone_regex],
        blank=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    position = models.CharField(
        max_length=50,
        choices=POSITION_CHOICES,
        default='front_desk'  
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.employee_id})"

class LeaveRequest(models.Model):
    employee = models.ForeignKey(EmployeeData, on_delete=models.CASCADE)
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=[('pending','Pending'),('approved','Approved'),('rejected','Rejected')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Leave request for {self.employee.name}"

class HRRequest(models.Model):
    TYPE_CHOICES = [
        ('remove_employee', 'Remove Employee'),
        ('add_employee', 'Add Employee'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    request_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    employee_data = models.JSONField(null=True, blank=True)  # For add requests
    employee = models.ForeignKey(
        EmployeeData, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )  # For remove requests
    request_by = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    processed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='processed_hr_requests'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_request_type_display()} request by {self.request_by.username}"

# Signal to create profile when user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        EmployeeProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
