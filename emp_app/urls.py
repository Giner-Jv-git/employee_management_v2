from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView
from .views import (
    EditEmployeeView, DeleteEmployeeView, EmployeeDetailView,
    add_employee, employee_profile, request_leave, approve_leave,
    attendance_list,leave_requests_admin, reject_leave,
    attendance_management, employee_clock_attendance, cancel_current_leave, early_return_from_leave,delete_attendance
)

urlpatterns = [
    # ---------------------------
    # Authentication
    # ---------------------------
    path('login/', views.login_view, name='login'),
    path('logout/confirm/', views.logout_confirm_view, name='logout_confirm'),
    path('logout/', views.logout_view, name='logout'),

    # ---------------------------
    # Admin Dashboard & Employee Management
    # ---------------------------
    path('dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('add-employee/', add_employee, name='add_employee'),
    path('employees/', views.EmployeeTableView.as_view(), name='view_table'),
    path('employee/<int:pk>/', EmployeeDetailView.as_view(), name='employee_detail'),
    path('employees/edit/<int:pk>/', EditEmployeeView.as_view(), name='edit_employee'),
    path('employees/delete/<int:pk>/', DeleteEmployeeView.as_view(), name='delete_employee'),

    # ---------------------------
    # Attendance Management
    # ---------------------------
    path('attendance-management/', attendance_management, name='attendance_management'),
    path('attendance/delete/<int:attendance_id>/', delete_attendance, name='delete_attendance'),
    

    # ---------------------------
    # Leave Management (Admin)
    # ---------------------------
    path('assign-leave/', views.assign_leave, name='assign_leave'),
    path('leave-requests/', leave_requests_admin, name='leave_requests_admin'),
    path('leave/<int:pk>/approve/', approve_leave, name='approve_leave'),
    path('leave/<int:pk>/reject/', reject_leave, name='reject_leave'),


    # ---------------------------
    # Employee Self-Service
    # ---------------------------
    path('employee/profile/', employee_profile, name='employee_profile'),
    path('employee/request_leave/', request_leave, name='request_leave'),
    path('employee/attendance/', attendance_list, name='attendance_list'),
    path('employee/clock-attendance/', employee_clock_attendance, name='employee_clock_attendance'),
    path('leave-history/', views.leave_history, name='leave_history'),
    path('cancel-current-leave/', cancel_current_leave, name='cancel_current_leave'),
    path('early-return-from-leave/', early_return_from_leave, name='early_return_from_leave'),
]