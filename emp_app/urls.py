from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView
from .views import (
     EditEmployeeView, DeleteEmployeeView, AdminEmployeeDetailView,
    add_employee, employee_profile, request_leave, approve_leave,
    payslip_list,
    attendance_list,
    add_payslip,
    add_attendance,
    leave_requests_admin,
    reject_leave,
    # Add these new imports
    attendance_management,
    payslip_management,
    employee_clock_attendance,
)
urlpatterns = [
    # auth
    path('login/', views.login_view, name='login'),
    path('logout/confirm/', views.logout_confirm_view, name='logout_confirm'),
    path('logout/', views.logout_view, name='logout'),
    # admin
    path('dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('add-employee/', views.add_employee, name='add_employee'),
    path('employees/edit/<int:pk>/', EditEmployeeView.as_view(), name='edit_employee'),
    path('employees/delete/<int:pk>/', DeleteEmployeeView.as_view(), name='delete_employee'),
    path('employees/', views.EmployeeTableView.as_view(), name='view_table'),
    path('employees/<int:pk>/', AdminEmployeeDetailView.as_view(), name='admin_employee_detail'),
    # ADD THESE NEW ADMIN MANAGEMENT URLS (to fix sidebar navigation)
    path('attendance-management/', views.attendance_management, name='attendance_management'),
    path('payslip-management/', views.payslip_management, name='payslip_management'),
    # employee self-service
    path('employee/profile/', employee_profile, name='employee_profile'),
    path('employee/request_leave/', request_leave, name='request_leave'),
    path('employee/payslips/', payslip_list, name='payslip_list'),
    path('employee/attendance/', attendance_list, name='attendance_list'),
    
    # Employee clock in/out
    path('employee/clock-attendance/', views.employee_clock_attendance, name='employee_clock_attendance'),
    # admin actions on employee data
    path('employees/<int:employee_id>/add-payslip/', add_payslip, name='add_payslip'),
    path('employees/<int:employee_id>/add-attendance/', add_attendance, name='add_attendance'),
    path('leave-requests/', leave_requests_admin, name='leave_requests_admin'),
    path('leave/<int:pk>/approve/', approve_leave, name='approve_leave'),
    path('leave/<int:pk>/reject/', reject_leave, name='reject_leave'),
    
    # ADD A GENERAL LEAVE REQUEST URL (to fix sidebar if needed)
    path('add-leave-request/', views.request_leave, name='add_leave_request'),
]