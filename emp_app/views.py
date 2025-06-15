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
from datetime import timedelta,datetime
from functools import wraps
from .models import EmployeeData, LeaveRequest, Attendance
from .forms import EmployeeForm,EditEmployeeForm,LeaveRequestForm, AdminLeaveAssignForm  
from django.contrib.auth.models import User

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
            
            # Get total approved leave days this year
            current_year = timezone.now().year
            approved_leaves_this_year = employee.leave_requests.filter(
                status='approved',
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
    paginate_by = 10
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
        self.object = self.get_object()
        user = self.object.user
        response = super().delete(request, *args, **kwargs)
        user.delete()
        messages.success(request, "Employee and user account deleted.")
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
    
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.employee = employee
            leave_request.save()
            messages.success(request, f"Leave request submitted for {leave_request.duration_days} days!")
            return redirect('request_leave')
    else:
        form = LeaveRequestForm()
    
    # Get employee's leave requests with better organization
    leave_requests = LeaveRequest.objects.filter(employee=employee).order_by('-created_at')
    pending_requests = leave_requests.filter(status='pending')
    approved_requests = leave_requests.filter(status='approved')
    
    # Calculate leave statistics
    current_year = timezone.now().year
    approved_days_this_year = sum([
        lr.duration_days for lr in approved_requests 
        if lr.start_date.year == current_year
    ])
    
    context = {
        'form': form,
        'leave_requests': leave_requests[:10],  # Recent 10
        'pending_requests': pending_requests,
        'approved_requests': approved_requests[:5],  # Recent 5 approved
        'approved_days_this_year': approved_days_this_year,
        'employee': employee
    }
    
    return render(request, 'emp_app/employee/request_leave.html', context)

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
    
    # Statistics
    stats = {
        'total_requests': requests.count(),
        'pending_requests': requests.filter(status='pending').count(),
        'approved_requests': requests.filter(status='approved').count(),
        'rejected_requests': requests.filter(status='rejected').count(),
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



@admin_required
def add_attendance(request, employee_id):
    employee = EmployeeData.objects.get(pk=employee_id)
    if request.method == 'POST':
        date = request.POST['date']
        time_in = request.POST['time_in']
        time_out = request.POST.get('time_out')
        status = request.POST['status']
        Attendance.objects.create(
            employee=employee,
            date=date,
            time_in=time_in,
            time_out=time_out,
            status=status
        )
        messages.success(request, f"Attendance added for {employee.name}!")
        return redirect('admin_employee_detail', pk=employee_id)
    return render(request, 'emp_app/admin/add_attendance.html', {'employee': employee})


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
    
    return render(request, 'emp_app/admin/attendance_management.html', {
        'employees': employees,
        'recent_attendance': recent_attendance,
        'working_employees': working_employees,
        'absent_employees': absent_employees,
    })

# Employee attendance view (for employees to clock in/out)
@employee_required
def employee_clock_attendance(request):  # New name to avoid conflicts
    """Employee clock in/out page with manual time entry"""
    employee = request.user.employee_profile
    today = timezone.now().date()
    current_time = timezone.now().strftime('%H:%M')
    
    # Get today's attendance
    today_attendance = Attendance.objects.filter(employee=employee, date=today).first()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'clock_in' and not today_attendance:
            time_in = request.POST.get('time_in')
            status = request.POST.get('status', 'present')
            
            Attendance.objects.create(
                employee=employee,
                date=today,
                time_in=time_in,
                status=status
            )
            messages.success(request, f'Successfully clocked in at {time_in}!')
            
        elif action == 'clock_out' and today_attendance and not today_attendance.time_out:
            time_out = request.POST.get('time_out')
            today_attendance.time_out = time_out
            today_attendance.save()
            messages.success(request, f'Successfully clocked out at {time_out}!')
        
        return redirect('employee_clock_attendance')
    
    return render(request, 'emp_app/employee/clock_attendance.html', {
        'today_attendance': today_attendance,
        'employee': employee,
        'current_time': current_time
    })