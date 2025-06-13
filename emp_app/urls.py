from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView
from .views import (
     EditEmployeeView, DeleteEmployeeView, AdminEmployeeDetailView,
    add_employee, employee_profile, request_leave, approve_leave
)


urlpatterns = [
    # auth
    path('login/', views.login_view, name='login'),
    path('logout/confirm/', views.logout_confirm_view, name='logout_confirm'),
    path('logout/', views.logout_view, name='logout'),  # confirmation page

    # admin
    path('dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('add-employee/', views.add_employee, name='add_employee'),
    path('employees/edit/<int:pk>/', EditEmployeeView.as_view(), name='edit_employee'),
    path('employees/delete/<int:pk>/', DeleteEmployeeView.as_view(), name='delete_employee'),
    path('employees/', views.EmployeeTableView.as_view(), name='view_table'),
    path('employees/<int:pk>/', AdminEmployeeDetailView.as_view(), name='admin_employee_detail'),

    # additional employee and leave management
    path('employee/profile/', employee_profile, name='employee_profile'),
    path('employee/request_leave/', request_leave, name='request_leave'),
    path('leave/<int:pk>/approve/', approve_leave, name='approve_leave'),
]