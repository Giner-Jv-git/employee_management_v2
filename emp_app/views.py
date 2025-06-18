from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, ListView, UpdateView, DeleteView, DetailView
from django.views.generic.edit import DeleteView
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q
from django.utils import timezone
from django.utils.crypto import get_random_string
from datetime import timedelta,datetime,time
from functools import wraps
from .models import EmployeeData, LeaveRequest, Attendance
from .forms import EmployeeForm,EditEmployeeForm,LeaveRequestForm, AdminLeaveAssignForm  
from django.contrib.auth.models import User
import csv
from django.http import HttpResponse
from django.conf import settings




def cleanup_expired_leaves():
    """Automatically update expired leave requests in bulk"""
    from django.utils import timezone
    today = timezone.now().date()
    
    return LeaveRequest.objects.filter(
        status='approved',
        end_date__lt=today
    ).update(status='completed')

# Custom Mixins for Role-Based Access Control
class AdminRequiredMixin(UserPassesTestMixin):
    """Only allow admin users (users without employee_profile)"""
    def test_func(self):
        return not hasattr(self.request.user, 'employee_profile')
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect('employee_profile')
        return super().handle_no_permission()

class EmployeeRequiredMixin(UserPassesTestMixin):
    """Only allow employee users (users with employee_profile)"""
    def test_func(self):
        return hasattr(self.request.user, 'employee_profile')
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect('admin_dashboard')
        return super().handle_no_permission()

# Decorators for Function-Based Views
def admin_required(view_func):
    """Decorator to require admin access for function-based views"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if hasattr(request.user, 'employee_profile'):
            return redirect('employee_profile')
        return view_func(request, *args, **kwargs)
    return wrapper

def employee_required(view_func):
    """Decorator to require employee access for function-based views"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not hasattr(request.user, 'employee_profile'):
            return redirect('admin_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

# Authentication Views
def login_view(request):
    if request.user.is_authenticated:
        # Redirect based on user type
        if hasattr(request.user, 'employee_profile'):
            return redirect('employee_profile')
        else:
            return redirect('admin_dashboard')
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Check if user is staff or has employee_profile
            if hasattr(user, 'employee_profile'):
                login(request, user)
                return redirect('employee_profile')
            elif user.is_staff or user.is_superuser:
                login(request, user)
                return redirect('admin_dashboard')
            else:
                # Not an employee or admin, deny access
                messages.error(request, 'Account not active or not authorized.')
                return render(request, 'emp_app/login.html')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'emp_app/login.html')

def logout_confirm_view(request):
    return render(request, 'emp_app/logout_confirm.html')

def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login')
    return redirect('logout_confirm')

# ADMIN VIEWS - Protected with AdminRequiredMixin
class AdminDashboardView(AdminRequiredMixin, TemplateView):
    template_name = 'emp_app/admin/dashboard.html'

    def get_context_data(self, **kwargs):
        # Clean up expired leaves first
        cleanup_expired_leaves()
        
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        # Get all employees with their leave requests
        all_employees = EmployeeData.objects.prefetch_related('leave_requests').all()
        
        # Count different employee states
        total_employees = all_employees.count()
        inactive_employees = all_employees.filter(status='inactive').count()
        
        # For active employees, check if they're currently on leave
        active_employees_available = 0
        employees_on_leave = 0
        
        for employee in all_employees.filter(status='active'):
            # Check if employee is currently on approved leave
            current_leave = employee.leave_requests.filter(
                status='approved',
                start_date__lte=today,
                end_date__gte=today
            ).first()
            
            if current_leave:
                employees_on_leave += 1
            else:
                active_employees_available += 1
        
        context['total_employees'] = total_employees
        context['active_employees'] = active_employees_available  # Actually available employees
        context['inactive_employees'] = employees_on_leave  # Employees currently on leave
        
        # Recent updates (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        context['recent_updates'] = EmployeeData.objects.filter(
            updated_at__gte=thirty_days_ago
        ).count()
        
        # Recently modified employees with enhanced leave status (last 5 changes)
        recent_employees = EmployeeData.objects.prefetch_related('leave_requests').order_by('-updated_at')[:5]
        
        # Add leave status to each recent employee
        for employee in recent_employees:
            # Check if employee is currently on approved leave
            current_leave = employee.leave_requests.filter(
                status='approved',
                start_date__lte=today,
                end_date__gte=today
            ).first()
            
            employee.current_leave = current_leave
            employee.is_on_leave = current_leave is not None
            
            # Get pending leave requests count
            employee.pending_leaves = employee.leave_requests.filter(status='pending').count()
            
            # Get total approved + completed leave days this year
            current_year = timezone.now().year
            approved_leaves_this_year = employee.leave_requests.filter(
                status__in=['approved', 'completed'],
                start_date__year=current_year
            )
            employee.total_leave_days_this_year = sum([
                leave.duration_days for leave in approved_leaves_this_year
            ])
        
        context['recent_employees'] = recent_employees
        
        # Pie chart data
        position_labels = [label for _, label in EmployeeData.POSITION_CHOICES]
        position_counts = [
            EmployeeData.objects.filter(position=key).count()
            for key, _ in EmployeeData.POSITION_CHOICES
        ]
        context['position_labels'] = position_labels
        context['position_counts'] = position_counts
        
        # Add additional context for better dashboard insights
        context['employees_on_leave_count'] = employees_on_leave
        context['truly_inactive_count'] = inactive_employees
        
        # Additional statistics for enhanced dashboard
        context['total_pending_leaves'] = LeaveRequest.objects.filter(status='pending').count()
        context['leaves_approved_this_month'] = LeaveRequest.objects.filter(
            status='approved',
            approved_at__gte=timezone.now().replace(day=1)
        ).count()
        context['total_completed_leaves'] = LeaveRequest.objects.filter(status='completed').count()
        
        return context

@admin_required
def add_employee(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            # Get username and password from the form (entered by admin)
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            try:
                # Check if user already exists
                if User.objects.filter(username=username).exists():
                    messages.error(request, 'Username already exists!')
                    return render(request, 'emp_app/admin/add_employee.html', {'form': form})
                
                # Create user with admin-provided credentials
                user = User.objects.create_user(username=username, password=password)
                
                # Create employee profile
                employee = form.save(commit=False)
                employee.user = user
                employee.created_by = request.user
                employee.save()
                
                messages.success(request, f'Employee added successfully! Username: {username}')
                return redirect('view_table')
                
            except Exception as e:
                messages.error(request, f'Error creating employee: {str(e)}')
                return render(request, 'emp_app/admin/add_employee.html', {'form': form})
    else:
        form = EmployeeForm()
    return render(request, 'emp_app/admin/add_employee.html', {'form': form})

class EmployeeTableView(AdminRequiredMixin, ListView):
    model = EmployeeData
    template_name = 'emp_app/admin/view_table.html'
    context_object_name = 'employees'
    paginate_by = 5
    def get_queryset(self):
        from django.utils import timezone
        
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        status_filter = self.request.GET.get('status', '')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(employee_id__icontains=search_query) |
                Q(phone_number__icontains=search_query) |
                Q(address__icontains=search_query)
            )
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        # Prefetch leave requests for better performance
        queryset = queryset.prefetch_related('leave_requests')
        
        return queryset.order_by('-created_at')
    def get_context_data(self, **kwargs):
        from django.utils import timezone
        
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['today'] = timezone.now().date()
        
        # Add leave status to each employee in the current page
        today = timezone.now().date()
        current_year = timezone.now().year
        
        for employee in context['employees']:
            # Check if employee is currently on leave
            current_leave = employee.leave_requests.filter(
                status='approved',
                start_date__lte=today,
                end_date__gte=today
            ).first()
            
            employee.current_leave = current_leave
            employee.is_on_leave = current_leave is not None
            
            # Get pending leave requests count
            employee.pending_leaves = employee.leave_requests.filter(status='pending').count()
            
            # Get total approved leave days this year
            approved_leaves_this_year = employee.leave_requests.filter(
                status='approved',
                start_date__year=current_year
            )
            employee.total_leave_days_this_year = sum([
                leave.duration_days for leave in approved_leaves_this_year
            ])
        
        # Add summary statistics for all employees (not just current page)
        all_employees = EmployeeData.objects.prefetch_related('leave_requests').all()
        employees_on_leave = 0
        employees_with_pending = 0
        employees_available = 0
        
        for emp in all_employees:
            current_leave = emp.leave_requests.filter(
                status='approved',
                start_date__lte=today,
                end_date__gte=today
            ).first()
            
            pending_count = emp.leave_requests.filter(status='pending').count()
            
            if current_leave:
                employees_on_leave += 1
            elif pending_count > 0:
                employees_with_pending += 1
            else:
                employees_available += 1
        
        context['summary_stats'] = {
            'total_employees': all_employees.count(),
            'employees_on_leave': employees_on_leave,
            'employees_with_pending': employees_with_pending,
            'employees_available': employees_available,
        }
        
        return context

class EditEmployeeView(AdminRequiredMixin, UpdateView):
    model = EmployeeData
    form_class = EditEmployeeForm  # Change from EmployeeForm to EditEmployeeForm
    template_name = 'emp_app/admin/edit_employee.html'
    success_url = reverse_lazy('view_table')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employee'] = self.get_object()
        return context
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Employee updated successfully!')
        return response

class DeleteEmployeeView(AdminRequiredMixin, DeleteView):
    model = EmployeeData
    template_name = 'emp_app/admin/confirm_delete.html'
    success_url = reverse_lazy('view_table')
    def delete(self, request, *args, **kwargs):
        # Store employee info before deletion
        employee = self.get_object()
        employee_name = employee.name
        user = employee.user
        
        # Call parent delete method
        response = super().delete(request, *args, **kwargs)
        
        # Delete associated user
        if user:
            user.delete()
        
        # Add success message
        messages.success(
            request, 
            f"🏖️ {employee_name} and their user account have been deleted from the beach!"
        )
        
        return response

class EmployeeDetailView(AdminRequiredMixin, DetailView):
    model = EmployeeData
    template_name = 'emp_app/admin/employee_detail.html'
    context_object_name = 'employee'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employee'] = self.get_object()
        return context

# EMPLOYEE VIEWS - Protected with EmployeeRequiredMixin
@employee_required
def employee_profile(request):
    employee = request.user.employee_profile
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
    else:
        form = EmployeeForm(instance=employee)
    return render(request, 'emp_app/employee/profile.html', {'form': form, 'employee': employee})


@employee_required
def request_leave(request):
    employee = request.user.employee_profile
    today = timezone.now().date()
    
    # Clean up expired leaves first
    cleanup_expired_leaves()
    
    # Check if employee is currently on approved leave
    current_leave = employee.leave_requests.filter(
        status='approved',
        start_date__lte=today,
        end_date__gte=today
    ).first()
    
    if current_leave:
        # If it's a POST request (form submission), show error and redirect
        if request.method == 'POST':
            messages.error(request, f"❌ You cannot request leave while currently on approved leave until {current_leave.end_date}!")
            return redirect('request_leave')  # Redirect instead of rendering
        
        # If it's a GET request, show the page with warning message
        messages.warning(request, f"⚠️ You are currently on approved leave until {current_leave.end_date}. You cannot submit new leave requests.")
        context = {
            'form': LeaveRequestForm(),
            'leave_requests': LeaveRequest.objects.filter(employee=employee).order_by('-created_at')[:10],
            'pending_requests': employee.leave_requests.filter(status='pending'),
            'approved_requests': employee.leave_requests.filter(status='approved')[:5],
            'approved_days_this_year': sum([
                lr.duration_days for lr in employee.leave_requests.filter(status='approved', start_date__year=timezone.now().year)
            ]),
            'employee': employee,
            'currently_on_leave': current_leave
        }
        return render(request, 'emp_app/employee/request_leave.html', context)
    
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            
            # Validate dates
            if start_date < today:
                messages.error(request, "❌ Start date cannot be in the past!")
                context = {
                    'form': form,
                    'leave_requests': LeaveRequest.objects.filter(employee=employee).order_by('-created_at')[:10],
                    'pending_requests': employee.leave_requests.filter(status='pending'),
                    'approved_requests': employee.leave_requests.filter(status='approved')[:5],
                    'approved_days_this_year': sum([
                        lr.duration_days for lr in employee.leave_requests.filter(status='approved', start_date__year=timezone.now().year)
                    ]),
                    'employee': employee
                }
                return render(request, 'emp_app/employee/request_leave.html', context)
            
            if end_date < start_date:
                messages.error(request, "❌ End date must be after or equal to start date!")
                context = {
                    'form': form,
                    'leave_requests': LeaveRequest.objects.filter(employee=employee).order_by('-created_at')[:10],
                    'pending_requests': employee.leave_requests.filter(status='pending'),
                    'approved_requests': employee.leave_requests.filter(status='approved')[:5],
                    'approved_days_this_year': sum([
                        lr.duration_days for lr in employee.leave_requests.filter(status='approved', start_date__year=timezone.now().year)
                    ]),
                    'employee': employee
                }
                return render(request, 'emp_app/employee/request_leave.html', context)
            
            # Check for overlapping requests (both pending and approved)
            overlapping = employee.leave_requests.filter(
                Q(status='approved') | Q(status='pending'),
                start_date__lte=end_date,
                end_date__gte=start_date
            )
            
            if overlapping.exists():
                overlapping_request = overlapping.first()
                messages.error(request, f"❌ You have a conflicting {overlapping_request.get_status_display()} leave request from {overlapping_request.start_date} to {overlapping_request.end_date}!")
                context = {
                    'form': form,
                    'leave_requests': LeaveRequest.objects.filter(employee=employee).order_by('-created_at')[:10],
                    'pending_requests': employee.leave_requests.filter(status='pending'),
                    'approved_requests': employee.leave_requests.filter(status='approved')[:5],
                    'approved_days_this_year': sum([
                        lr.duration_days for lr in employee.leave_requests.filter(status='approved', start_date__year=timezone.now().year)
                    ]),
                    'employee': employee
                }
                return render(request, 'emp_app/employee/request_leave.html', context)
            
            # All validations passed - save the leave request
            leave_request = form.save(commit=False)
            leave_request.employee = employee
            leave_request.save()
            
            messages.success(request, f"✅ Leave request submitted successfully for {leave_request.duration_days} days from {start_date} to {end_date}!")
            return redirect('request_leave')
    else:
        form = LeaveRequestForm()
    
    # Get employee's leave requests with better organization
    leave_requests = LeaveRequest.objects.filter(employee=employee).order_by('-created_at')
    pending_requests = leave_requests.filter(status='pending')
    approved_requests = leave_requests.filter(status='approved')
    completed_requests = leave_requests.filter(status='completed')
    
    # Calculate leave statistics
    current_year = timezone.now().year
    approved_days_this_year = sum([
        lr.duration_days for lr in approved_requests 
        if lr.start_date.year == current_year
    ])
    
    completed_days_this_year = sum([
        lr.duration_days for lr in completed_requests 
        if lr.start_date.year == current_year
    ])
    
    context = {
        'form': form,
        'leave_requests': leave_requests[:10],  # Recent 10
        'pending_requests': pending_requests,
        'approved_requests': approved_requests[:5],  # Recent 5 approved
        'completed_requests': completed_requests[:5],  # Recent 5 completed
        'approved_days_this_year': approved_days_this_year,
        'completed_days_this_year': completed_days_this_year,
        'total_leave_days_this_year': approved_days_this_year + completed_days_this_year,
        'employee': employee,
        'currently_on_leave': current_leave
    }
    
    return render(request, 'emp_app/employee/request_leave.html', context)

@employee_required
def cancel_current_leave(request):
    if request.method == 'POST':
        employee = request.user.employee_profile
        today = timezone.now().date()
        
        # Find current active leave
        current_leave = employee.leave_requests.filter(
            status='approved',
            start_date__lte=today,
            end_date__gte=today
        ).first()
        
        if current_leave:
            # Cancel the leave by updating end date to yesterday
            yesterday = today - timedelta(days=1)
            current_leave.end_date = yesterday
            current_leave.status = 'completed'
            current_leave.comments = f"Cancelled by employee on {today}"
            current_leave.save()
            
            messages.success(request, f"✅ Your leave has been cancelled successfully! You are now back to work.")
            return redirect('request_leave')
        else:
            messages.error(request, "❌ No active leave found to cancel.")
            return redirect('request_leave')
    
    return redirect('request_leave')

@employee_required
def early_return_from_leave(request):
    if request.method == 'POST':
        employee = request.user.employee_profile
        today = timezone.now().date()
        
        # Find current active leave
        current_leave = employee.leave_requests.filter(
            status='approved',
            start_date__lte=today,
            end_date__gte=today
        ).first()
        
        if current_leave:
            original_end_date = current_leave.end_date
            days_saved = (original_end_date - today).days
            
            # End leave today
            current_leave.end_date = today
            current_leave.status = 'completed'
            current_leave.comments = f"Early return by employee on {today}. Original end date was {original_end_date}."
            current_leave.save()
            
            messages.success(request, f"✅ Welcome back! You returned {days_saved} day{'s' if days_saved != 1 else ''} early from your leave.")
            return redirect('request_leave')
        else:
            messages.error(request, "❌ No active leave found.")
            return redirect('request_leave')
    
    return redirect('request_leave')

@employee_required
def leave_history(request):
    employee = request.user.employee_profile
    
    # Get all leave requests for this employee
    leave_requests = LeaveRequest.objects.filter(employee=employee).order_by('-created_at')
    
    # Get statistics
    total_requests = leave_requests.count()
    approved_requests = leave_requests.filter(status='approved')
    pending_requests = leave_requests.filter(status='pending')
    rejected_requests = leave_requests.filter(status='rejected')
    
    # Calculate total approved days this year
    current_year = timezone.now().year
    approved_days_this_year = sum([
        lr.duration_days for lr in approved_requests 
        if lr.start_date.year == current_year
    ])
    
    context = {
        'leave_requests': leave_requests,
        'total_requests': total_requests,
        'approved_requests': approved_requests,
        'pending_requests': pending_requests,
        'rejected_requests': rejected_requests,
        'approved_days_this_year': approved_days_this_year,
        'employee': employee
    }
    
    return render(request, 'emp_app/employee/leave_history.html', context)

@admin_required
def leave_requests_admin(request):
    # Clean up expired leaves first
    cleanup_expired_leaves()
    
    # Filter options
    status_filter = request.GET.get('status', '')
    employee_filter = request.GET.get('employee', '')
    date_filter = request.GET.get('date_range', '')
    
    requests = LeaveRequest.objects.select_related('employee', 'approved_by').order_by('-created_at')
    
    # Apply filters
    if status_filter:
        requests = requests.filter(status=status_filter)
    if employee_filter:
        requests = requests.filter(employee_id=employee_filter)
    if date_filter == 'this_month':
        start_of_month = timezone.now().replace(day=1)
        requests = requests.filter(created_at__gte=start_of_month)
    elif date_filter == 'this_week':
        start_of_week = timezone.now() - timedelta(days=timezone.now().weekday())
        requests = requests.filter(created_at__gte=start_of_week)
    
    # Statistics (added completed requests)
    stats = {
        'total_requests': requests.count(),
        'pending_requests': requests.filter(status='pending').count(),
        'approved_requests': requests.filter(status='approved').count(),
        'rejected_requests': requests.filter(status='rejected').count(),
        'completed_requests': requests.filter(status='completed').count(),
    }
    
    context = {
        'requests': requests[:20],  # Paginate later
        'stats': stats,
        'employees': EmployeeData.objects.filter(status='active'),
        'status_filter': status_filter,
        'employee_filter': employee_filter,
        'date_filter': date_filter,
    }
    
    return render(request, 'emp_app/admin/leave_requests.html', context)

@admin_required
def assign_leave(request):
    if request.method == 'POST':
        form = AdminLeaveAssignForm(request.POST)
        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.assigned_by_admin = True
            leave_request.status = 'approved'  # Admin-assigned leave is auto-approved
            leave_request.approved_by = request.user
            leave_request.approved_at = timezone.now()
            leave_request.save()
            
            messages.success(request, f"Leave assigned to {leave_request.employee.name} for {leave_request.duration_days} days!")
            return redirect('leave_requests_admin')
    else:
        form = AdminLeaveAssignForm()
    
    return render(request, 'emp_app/admin/assign_leave.html', {'form': form})


@admin_required
def approve_leave(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    leave.status = 'approved'
    leave.approved_by = request.user
    leave.approved_at = timezone.now()
    leave.save()
    
    messages.success(request, f"Leave approved for {leave.employee.name} ({leave.duration_days} days)")
    return redirect('leave_requests_admin')

@admin_required
def reject_leave(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    leave.status = 'rejected'
    leave.approved_by = request.user
    leave.approved_at = timezone.now()
    leave.save()
    
    messages.success(request, f"Leave rejected for {leave.employee.name}")
    return redirect('leave_requests_admin')



@employee_required
def attendance_list(request):
    attendance = Attendance.objects.filter(employee=request.user.employee_profile).order_by('-date')
    return render(request, 'emp_app/employee/attendance_list.html', {'attendance': attendance})


#attendance

@admin_required
def attendance_management(request):
    from django.utils import timezone
    
    today = timezone.now().date()
    employees = EmployeeData.objects.all()
    recent_attendance = Attendance.objects.select_related('employee').order_by('-date')[:20]
    
    # Get today's attendance for all employees
    today_attendance = Attendance.objects.filter(date=today)
    
    # Add today's attendance to each employee
    for employee in employees:
        employee.today_attendance = today_attendance.filter(employee=employee).first()
    
    # Calculate statistics for the dashboard
    working_employees = today_attendance.filter(time_out__isnull=True)
    absent_employees = employees.exclude(
        id__in=today_attendance.values_list('employee_id', flat=True)
    )
    
    # Calculate counts for template
    present_count = today_attendance.filter(status='present').count()
    late_count = today_attendance.filter(status='late').count()
    absent_count = absent_employees.count()
    working_count = working_employees.count()
    
    return render(request, 'emp_app/admin/attendance_management.html', {
        'employees': employees,
        'recent_attendance': recent_attendance,
        'working_employees': working_employees,
        'absent_employees': absent_employees,
        'today': today,
        'present_count': present_count + late_count,  # Present + Late = Total showed up
        'absent_count': absent_count,
        'working_count': working_count,
    })






def get_philippines_time():
    """Get Philippines time by adding 8 hours to UTC"""
    utc_time = timezone.now()
    philippines_time = utc_time + timedelta(hours=8)
    return philippines_time

@login_required
def employee_clock_attendance(request):
    try:
        if hasattr(request.user, 'employeedata'):
            employee = request.user.employeedata
        else:
            employee = EmployeeData.objects.get(user=request.user)
    except:
        messages.error(request, "🏖️ Employee profile not found!")
        return redirect('dashboard')
    
    # Get Philippines time (UTC+8)
    current_time = get_philippines_time()
    today = current_time.date()
    
    today_attendance = Attendance.objects.filter(employee=employee, date=today).first()
    
    # Define work schedule times for COMPARISON (not display)
    work_start_time = datetime.combine(today, datetime.min.time().replace(hour=9, minute=0))
    late_threshold = datetime.combine(today, datetime.min.time().replace(hour=9, minute=15))
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'clock_in':
            if today_attendance and today_attendance.time_in:
                messages.warning(request, "🏖️ You've already clocked in today!")
            else:
                ph_time = get_philippines_time()
                
                # Create datetime object for comparison
                clock_in_datetime = datetime.combine(today, ph_time.time())
                
                # Determine status by comparing DATETIME objects
                if clock_in_datetime <= work_start_time:
                    status = 'present'
                    message = f"🌅 Perfect timing, {employee.name}! Early bird gets the best waves!"
                elif clock_in_datetime <= late_threshold:
                    status = 'present'
                    message = f"🌅 Good morning, {employee.name}! Just made it on time!"
                else:
                    status = 'late'
                    message = f"⏰ Hello {employee.name}! You're late, but the tropical beach is still beautiful!"
                
                print(f"Clock in time: {clock_in_datetime}")
                print(f"Work start: {work_start_time}")
                print(f"Late threshold: {late_threshold}")
                print(f"Status: {status}")
                
                if today_attendance:
                    today_attendance.time_in = ph_time.time()
                    today_attendance.status = status
                    today_attendance.save()
                else:
                    today_attendance = Attendance.objects.create(
                        employee=employee,
                        date=today,
                        time_in=ph_time.time(),
                        status=status
                    )
                
                messages.success(request, message)
        
        elif action == 'clock_out':
            if today_attendance and today_attendance.time_in and not today_attendance.time_out:
                ph_time = get_philippines_time()
                today_attendance.time_out = ph_time.time()
                today_attendance.save()
                messages.success(request, f"🌇 Great day {employee.name}! Clocked out at {ph_time.strftime('%I:%M %p')}")
            else:
                messages.error(request, "🏖️ Can't clock out - check your status!")
        
        return redirect('employee_clock_attendance')
    
    context = {
        'employee': employee,
        'today_attendance': today_attendance,
        'today': today,
        'current_time': current_time,
        'work_start_time': current_time.replace(hour=9, minute=0),
        'late_threshold': current_time.replace(hour=9, minute=15),
    }
    
    return render(request, 'emp_app/employee/clock_attendance.html', context)




# Employee attendance view (for employees to clock in/out)


@admin_required
def delete_attendance(request, attendance_id):
    """Delete an attendance record"""
    attendance = get_object_or_404(Attendance, pk=attendance_id)
    
    if request.method == 'POST':
        employee_name = attendance.employee.name
        attendance_date = attendance.date
        attendance.delete()
        messages.success(request, f"🏖️ Beach record for {employee_name} on {attendance_date} has been deleted!")
        return redirect('attendance_management')
    
    return render(request, 'emp_app/admin/delete_attendance.html', {'attendance': attendance})