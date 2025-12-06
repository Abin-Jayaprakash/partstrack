"""URL configuration for the inventory app."""
from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.custom_login, name="login"),
    path("logout/", views.custom_logout, name="logout"),

    path("dashboard/", views.dashboard, name="dashboard"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path(
        "employee-dashboard/",
        views.employee_dashboard,
        name="employee_dashboard",
    ),

    path(
        "employee-parts/",
        views.employee_parts_list,
        name="employee_parts_list",
    ),
    path(
        "employee-parts/add/",
        views.employee_add_part,
        name="employee_add_part",
    ),
    path(
        "employee-parts/edit/<int:pk>/",
        views.employee_edit_part,
        name="employee_edit_part",
    ),
    path(
        "employee-parts/delete/<int:pk>/",
        views.employee_delete_part,
        name="employee_delete_part",
    ),

    path("parts/", views.spare_parts_list, name="spare_parts_list"),
    path("parts/add/", views.add_part, name="add_part"),
    path("parts/edit/<int:pk>/", views.edit_part, name="edit_part"),
    path("parts/delete/<int:pk>/", views.delete_part, name="delete_part"),

    path("employees/", views.employees_list, name="employees_list"),
    path("employees/add/", views.add_employee, name="add_employee"),
    path(
        "employees/edit/<int:user_id>/",
        views.edit_employee,
        name="edit_employee",
    ),
    path(
        "employees/deactivate/<int:user_id>/",
        views.deactivate_employee,
        name="deactivate_employee",
    ),

    path("sales/", views.sales_list, name="sales_list"),
    path("suppliers/add/", views.add_supplier, name="add_supplier"),
    path(
        "suppliers/<int:supplier_id>/edit/",
        views.edit_supplier,
        name="edit_supplier",
    ),
    path(
        "suppliers/<int:supplier_id>/delete/",
        views.delete_supplier,
        name="delete_supplier",
    ),

    path(
        "force-password-change/",
        views.force_password_change,
        name="force_password_change",
    ),
    path("purchase-list/", views.purchase_list, name="purchase_list"),

    path(
        "api/stock-status/",
        views.get_stock_status_data,
        name="get_stock_status_data",
    ),
    path(
        "api/top-parts/",
        views.get_top_parts_data,
        name="get_top_parts_data",
    ),
]
