from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import RegexValidator

class EmployeeProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        
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
    LEAVE_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),  # Added this
    ]
    
    LEAVE_TYPE_CHOICES = [
        ('sick', 'Sick Leave'),
        ('vacation', 'Vacation Leave'),
        ('personal', 'Personal Leave'),
        ('emergency', 'Emergency Leave'),
        ('other', 'Other'),
    ]
    
    employee = models.ForeignKey(EmployeeData, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES, default='other')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=LEAVE_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves')
    approved_at = models.DateTimeField(null=True, blank=True)
    comments = models.TextField(blank=True, help_text="Admin comments on the leave request")
    
    # For admin-assigned leave
    assigned_by_admin = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.employee.name} - {self.get_leave_type_display()} ({self.start_date} to {self.end_date})"
    
    @property
    def duration_days(self):
        return (self.end_date - self.start_date).days + 1
    
    @property
    def is_active(self):
        from django.utils import timezone
        today = timezone.now().date()
        return self.status == 'approved' and self.start_date <= today <= self.end_date
    
    def update_status_if_expired(self):
        """Check if this leave request has expired and update status"""
        from django.utils import timezone
        if self.status == 'approved' and self.end_date < timezone.now().date():
            self.status = 'completed'
            self.save()
            return True
        return False
    
    @classmethod
    def cleanup_expired_leaves(cls):
        """Bulk update all expired approved leaves to completed status"""
        from django.utils import timezone
        today = timezone.now().date()
        
        return cls.objects.filter(
            status='approved',
            end_date__lt=today
        ).update(status='completed')



class Attendance(models.Model):
    employee = models.ForeignKey(EmployeeData, on_delete=models.CASCADE)
    date = models.DateField()
    time_in = models.TimeField(null=True, blank=True)  # Fixed: Allow null values
    time_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('present', 'Present'), 
        ('absent', 'Absent'),
        ('late', 'Late'),  # Added for beach theme
    ], default='absent')
    
    class Meta:
        unique_together = ('employee', 'date')
        
    def __str__(self):
        return f"{self.employee.name} - {self.date}"
    
    def get_status_display(self):
        status_dict = {
            'present': 'Present',
            'absent': 'Absent', 
            'late': 'Late'
        }
        return status_dict.get(self.status, self.status)
    
    @property
    def work_duration(self):
        """Calculate work duration"""
        if self.time_in and self.time_out:
            from datetime import datetime
            time_in_dt = datetime.combine(self.date, self.time_in)
            time_out_dt = datetime.combine(self.date, self.time_out)
            duration = time_out_dt - time_in_dt
            
            hours = duration.seconds // 3600
            minutes = (duration.seconds % 3600) // 60
            return {'hours': hours, 'minutes': minutes}
        return None