from django.urls import path
from . import views

urlpatterns = [
    # Home Route
    path('', views.home, name='home'),
    
    # Login & Logout
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    
    # Dashboard Routes - Main entry point
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('employee-dashboard/', views.employee_dashboard, name='employee_dashboard'),
    
    # Employee Parts Routes (CRUD with full permissions)
    path('employee-parts/', views.employee_parts_list, name='employee_parts_list'),
    path('employee-parts/add/', views.employee_add_part, name='employee_add_part'),
    path('employee-parts/edit/<int:pk>/', views.employee_edit_part, name='employee_edit_part'),
    path('employee-parts/delete/<int:pk>/', views.employee_delete_part, name='employee_delete_part'),
    
    # Employee Analytics Routes (disabled)
    # path('employee-analytics/', views.employee_analytics, name='employee_analytics'),
    
    # Admin Parts Routes (CRUD)
    path('parts/', views.spare_parts_list, name='spare_parts_list'),
    path('parts/add/', views.add_part, name='add_part'),
    path('parts/edit/<int:pk>/', views.edit_part, name='edit_part'),
    path('parts/delete/<int:pk>/', views.delete_part, name='delete_part'),
    
    # Admin Analytics Routes (disabled)
    # path('admin-analytics/', views.admin_analytics, name='admin_analytics'),
    
    # Employees Routes
    path('employees/', views.employees_list, name='employees_list'),
    path('employees/add/', views.add_employee, name='add_employee'),
    path('employees/edit/<int:user_id>/', views.edit_employee, name='edit_employee'),
    path(
        'employees/deactivate/<int:user_id>/',
        views.deactivate_employee,
        name='deactivate_employee'
    ),
    
    # Sales Routes
    path('sales/', views.sales_list, name='sales_list'),
    
    # Force password change (first login)
    path('force-password-change/', views.force_password_change, name='force_password_change'),
    
    # Stock purchase list (CSV)
    path('purchase-list/', views.purchase_list, name='purchase_list'),
    
    # API Routes
    path('api/stock-status/', views.get_stock_status_data, name='get_stock_status_data'),
    path('api/top-parts/', views.get_top_parts_data, name='get_top_parts_data'),
]
