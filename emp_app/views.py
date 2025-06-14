from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, ListView, UpdateView, DeleteView, DetailView
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q
from django.utils import timezone
from django.utils.crypto import get_random_string
from datetime import timedelta
from functools import wraps
from .models import EmployeeData, LeaveRequest, PaySlip, Attendance
from .forms import EmployeeForm
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
        context['total_employees'] = EmployeeData.objects.count()
        context['active_employees'] = EmployeeData.objects.filter(status='active').count()
        context['inactive_employees'] = EmployeeData.objects.filter(status='inactive').count()
        
        # Recent updates (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        context['recent_updates'] = EmployeeData.objects.filter(
            updated_at__gte=thirty_days_ago
        ).count()
        
        # Recently modified employees (last 5 changes)
        context['recent_employees'] = EmployeeData.objects.all().order_by('-updated_at')[:5]
        
        # Pie chart data
        position_labels = [label for _, label in EmployeeData.POSITION_CHOICES]
        position_counts = [
            EmployeeData.objects.filter(position=key).count()
            for key, _ in EmployeeData.POSITION_CHOICES
        ]
        context['position_labels'] = position_labels
        context['position_counts'] = position_counts
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

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        return context

class EditEmployeeView(AdminRequiredMixin, UpdateView):
    model = EmployeeData
    form_class = EmployeeForm
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
    success_url = reverse_lazy('view_table')
    template_name = 'emp_app/admin/confirm_delete.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employee'] = self.get_object()
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Employee deleted successfully!')
        return response

class AdminEmployeeDetailView(AdminRequiredMixin, DetailView):
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
        reason = request.POST.get('reason')
        LeaveRequest.objects.create(employee=employee, reason=reason)
        messages.success(request, "Leave request submitted!")
    leave_requests = LeaveRequest.objects.filter(employee=employee).order_by('-created_at')
    return render(request, 'emp_app/employee/request_leave.html', {'leave_requests': leave_requests})

@admin_required
def leave_requests_admin(request):
    requests = LeaveRequest.objects.select_related('employee').order_by('-created_at')
    return render(request, 'emp_app/admin/leave_requests.html', {'requests': requests})

@admin_required
def approve_leave(request, pk):
    leave = LeaveRequest.objects.get(pk=pk)
    leave.status = 'approved'
    leave.save()
    leave.employee.status = 'inactive'  # Optional: set employee inactive on approval
    leave.employee.save()
    messages.success(request, "Leave approved and employee set to inactive.")
    return redirect('leave_requests_admin')

@admin_required
def reject_leave(request, pk):
    leave = LeaveRequest.objects.get(pk=pk)
    leave.status = 'rejected'
    leave.save()
    messages.success(request, "Leave rejected.")
    return redirect('leave_requests_admin')

@employee_required
def payslip_list(request):
    payslips = PaySlip.objects.filter(employee=request.user.employee_profile).order_by('-issued_at')
    return render(request, 'emp_app/employee/payslip_list.html', {'payslips': payslips})

@employee_required
def attendance_list(request):
    attendance = Attendance.objects.filter(employee=request.user.employee_profile).order_by('-date')
    return render(request, 'emp_app/employee/attendance_list.html', {'attendance': attendance})

@admin_required
def add_payslip(request, employee_id):
    employee = EmployeeData.objects.get(pk=employee_id)
    if request.method == 'POST':
        period_start = request.POST['period_start']
        period_end = request.POST['period_end']
        amount = request.POST['amount']
        notes = request.POST.get('notes', '')
        PaySlip.objects.create(
            employee=employee,
            period_start=period_start,
            period_end=period_end,
            amount=amount,
            notes=notes
        )
        messages.success(request, "Pay slip added!")
        return redirect('admin_employee_detail', pk=employee_id)
    return render(request, 'emp_app/admin/add_payslip.html', {'employee': employee})

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
@admin_required
def payslip_management(request):
    employees = EmployeeData.objects.all()
    recent_payslips = PaySlip.objects.select_related('employee').order_by('-issued_at')[:20]
    return render(request, 'emp_app/admin/payslip_management.html', {
        'employees': employees,
        'recent_payslips': recent_payslips
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