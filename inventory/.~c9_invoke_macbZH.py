"""Inventory app views (cleaned).

This file contains Django views for the inventory app.
"""
# pylint: disable=no-member,broad-except,too-few-public-methods

# Standard library
import csv
import uuid

# Django / third-party
from django import forms
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import models
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

# Local app
from .forms import EmployeeForm, SparePartForm
from .models import Sale, SparePart, UserProfile, Supplier


class EmployeeUpdateForm(forms.ModelForm):
    """Form used to update basic employee details (admin-only)."""

    mobile_number = forms.CharField(required=False)

    class Meta:
        """Metadata for EmployeeUpdateForm."""
        model = User
        fields = ["first_name", "last_name", "email"]


def home(request):
    """Redirect to dashboard if authenticated; otherwise to login."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("login")


def custom_login(request):
    """Login view that accepts username or email and sets user role."""
    if request.method == "POST":
        username_or_email = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username_or_email,
            password=password,
        )

        if user is None:
            try:
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(
                    request,
                    username=user_obj.username,
                    password=password,
                )
            except User.DoesNotExist:
                user = None

        if user is not None and user.is_active:
            profile, created = UserProfile.objects.get_or_create(user=user)
            if user.is_staff or user.is_superuser:
                if created or profile.role != "admin":
                    profile.role = "admin"
                    profile.save()
            else:
                if created or profile.role != "employee":
                    profile.role = "employee"
                    profile.save()

            login(request, user)

            if getattr(profile, "must_change_password", False):
                return redirect("force_password_change")

            return redirect("dashboard")

        return render(
            request,
            "inventory/login.html",
            {"error": "Invalid username/email or password"},
        )

    return render(request, "inventory/login.html")


def custom_logout(request):
    """Log the user out and redirect to login page."""
    logout(request)
    return redirect("login")


@login_required(login_url="login")
def dashboard(request):
    """Route users to admin or employee dashboards depending on permissions."""
    if request.user.is_staff or request.user.is_superuser:
        return redirect("admin_dashboard")
    return redirect("employee_dashboard")


@login_required(login_url="login")
def admin_dashboard(request):
    """Admin dashboard view with summary statistics for parts and sales."""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("employee_dashboard")

    parts = SparePart.objects.all()
    low_stock_parts = parts.filter(quantity__lte=models.F("minimum_stock"))
    out_of_stock_parts = parts.filter(quantity=0)

    total_parts = parts.count()
    low_stock_count = low_stock_parts.count()
    out_of_stock_count = out_of_stock_parts.count()
    stock_value = sum(p.quantity * p.price for p in parts)
    sales_count = Sale.objects.count()
    sales_revenue = sum(s.total_price for s in Sale.objects.all())
    in_stock = parts.filter(quantity__gt=models.F("minimum_stock")).count()

    context = {
        "parts": parts,
        "user_role": "admin",
        "total_parts": total_parts,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "stock_value": f"{stock_value:.2f}",
        "sales_count": sales_count,
        "sales_revenue": f"{sales_revenue:.2f}",
        "low_stock_alerts": low_stock_parts[:5],
        "in_stock": in_stock,
    }
    return render(request, "inventory/admin_dashboard.html", context)


@login_required(login_url="login")
def employee_dashboard(request):
    """Employee dashboard with a simplified summary."""
    if request.user.is_staff or request.user.is_superuser:
        return redirect("admin_dashboard")

    parts = SparePart.objects.all()
    low_stock_parts = parts.filter(quantity__lte=models.F("minimum_stock"))

    in_stock = parts.filter(quantity__gt=models.F("minimum_stock")).count()
    out_of_stock = parts.filter(quantity=0).count()
    total_parts = parts.count()
    low_stock_count = low_stock_parts.count()

    sales = Sale.objects.all()
    total_sales = sales.count()
    total_revenue = sum(s.total_price for s in sales)

    context = {
        "user_role": "employee",
        "total_parts": total_parts,
        "low_stock_count": low_stock_count,
        "in_stock": in_stock,
        "out_of_stock": out_of_stock,
        "total_sales": total_sales,
        "total_revenue": f"{total_revenue:.2f}",
        "low_stock_alerts": low_stock_parts[:5],
    }
    return render(request, "inventory/employee_dashboard.html", context)


@login_required(login_url="login")
def get_stock_status_data(request):
    """Return JSON with counts of in/low/out-of-stock parts."""
    try:
        parts = SparePart.objects.all()
        in_stock = parts.filter(
            quantity__gt=models.F("minimum_stock"),
        ).count()
        low_stock = parts.filter(
            quantity__lte=models.F("minimum_stock"),
            quantity__gt=0,
        ).count()
        out_of_stock = parts.filter(quantity=0).count()

        data = {
            "in_stock": in_stock,
            "low_stock": low_stock,
            "out_of_stock": out_of_stock,
            "total": in_stock + low_stock + out_of_stock,
            "timestamp": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            "success": True,
        }
        return JsonResponse(data)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return JsonResponse(
            {"error": str(exc), "success": False},
            status=500,
        )


@login_required(login_url="login")
def get_top_parts_data(request):
    """Return JSON with top parts (by quantity sold) for charts."""
    try:
        top_parts = (
            Sale.objects.values("part__part_name")
            .annotate(total_quantity=Sum("quantity_sold"))
            .order_by("-total_quantity")[:5]
        )

        if top_parts:
            labels = [item["part__part_name"] for item in top_parts]
            quantities = [item["total_quantity"] for item in top_parts]
        else:
            fallback_parts = SparePart.objects.all().order_by("-quantity")[:5]
            labels = [p.part_name for p in fallback_parts]
            quantities = [p.quantity for p in fallback_parts]

        data = {
            "labels": labels or ["No data"],
            "quantities": quantities or [0],
            "timestamp": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            "success": True,
        }
        return JsonResponse(data)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return JsonResponse(
            {
                "error": str(exc),
                "labels": ["Error"],
                "quantities": [0],
                "success": False,
            },
            status=500,
        )


@login_required(login_url="login")
def employee_parts_list(request):
    """Employee-facing parts listing with optional search and stock filtering."""
    if request.user.is_staff or request.user.is_superuser:
        return redirect("spare_parts_list")

    parts = SparePart.objects.all()
    query = request.GET.get("q", "").strip()
    stock_filter = request.GET.get("stock_filter", "")

    if query:
        parts = parts.filter(
            models.Q(part_name__icontains=query)
            | models.Q(part_number__icontains=query),
        )

    if stock_filter == "low":
        parts = parts.filter(
            quantity__lte=models.F("minimum_stock"),
            quantity__gt=0,
        )
    elif stock_filter == "out":
        parts = parts.filter(quantity=0)

    low_stock_parts = parts.filter(quantity__lte=models.F("minimum_stock"))
    out_of_stock_parts = parts.filter(quantity=0)
    total_parts = parts.count()
    low_stock_count = low_stock_parts.count()
    out_of_stock_count = out_of_stock_parts.count()
    stock_value = sum(p.quantity * p.price for p in parts)

    context = {
        "parts": parts,
        "user_role": "employee",
        "total_parts": total_parts,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "stock_value": f"{stock_value:.2f}",
        "low_stock_alerts": low_stock_parts[:5],
        "is_employee": True,
    }
    return render(request, "inventory/employee_parts_list.html", context)


@login_required(login_url="login")
def employee_add_part(request):
    """Allow employee to add a part."""
    if request.user.is_staff or request.user.is_superuser:
        return redirect("add_part")

    if request.method == "POST":
        form = SparePartForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("employee_parts_list")
    else:
        form = SparePartForm()

    return render(
        request,
        "inventory/employee_add_part.html",
        {"form": form, "user_role": "employee"},
    )


@login_required(login_url="login")
def employee_edit_part(request, pk):
    """Allow employee to edit a part."""
    if request.user.is_staff or request.user.is_superuser:
        return redirect("edit_part", pk=pk)

    part = get_object_or_404(SparePart, pk=pk)
    if request.method == "POST":
        form = SparePartForm(request.POST, instance=part)
        if form.is_valid():
            form.save()
            return redirect("employee_parts_list")
    else:
        form = SparePartForm(instance=part)

    return render(
        request,
        "inventory/employee_edit_part.html",
        {"form": form, "part": part, "user_role": "employee"},
    )


@login_required(login_url="login")
def employee_delete_part(request, pk):
    """Allow employee to delete a part."""
    if request.user.is_staff or request.user.is_superuser:
        return redirect("delete_part", pk=pk)

    part = get_object_or_404(SparePart, pk=pk)
    if request.method == "POST":
        part.delete()
        return redirect("employee_parts_list")

    return render(
        request,
        "inventory/employee_delete_part.html",
        {"part": part, "user_role": "employee"},
    )


@login_required(login_url="login")
def employee_analytics(request):  # pylint: disable=unused-argument
    """Placeholder: redirect employee analytics to appropriate dashboard."""
    if request.user.is_staff or request.user.is_superuser:
        return redirect("admin_analytics")
    return redirect("employee_dashboard")


@login_required(login_url="login")
def admin_analytics(request):
    """Admin analytics page with stock and sales summary."""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("employee_dashboard")

    parts = SparePart.objects.all()
    in_stock = parts.filter(
        quantity__gt=models.F("minimum_stock"),
    ).count()
    low_stock = parts.filter(
        quantity__lte=models.F("minimum_stock"),
        quantity__gt=0,
    ).count()
    out_of_stock = parts.filter(quantity=0).count()

    sales = Sale.objects.all()
    total_sales = sales.count()
    total_revenue = sum(s.total_price for s in sales)

    context = {
        "user_role": "admin",
        "total_parts": parts.count(),
        "low_stock_count": low_stock,
        "in_stock": in_stock,
        "out_of_stock": out_of_stock,
        "total_sales": total_sales,
        "total_revenue": f"{total_revenue:.2f}",
        "low_stock_alerts": parts.filter(quantity__lte=models.F("minimum_stock"))[
            :5
        ],
    }
    return render(request, "inventory/admin_analytics.html", context)


@login_required(login_url="login")
def spare_parts_list(request):
    """Admin-facing spare parts list."""
    parts = SparePart.objects.all()
    low_stock_parts = parts.filter(quantity__lte=models.F("minimum_stock"))
    out_of_stock_parts = parts.filter(quantity=0)
    stock_value = sum(p.quantity * p.price for p in parts)

    context = {
        "parts": parts,
        "user_role": "admin",
        "total_parts": parts.count(),
        "low_stock_count": low_stock_parts.count(),
        "out_of_stock_count": out_of_stock_parts.count(),
        "stock_value": f"{stock_value:.2f}",
        "low_stock_alerts": low_stock_parts[:5],
    }
    return render(request, "inventory/parts_list.html", context)


@login_required(login_url="login")
def add_part(request):
    """Admin add part view."""
    if request.method == "POST":
        form = SparePartForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("spare_parts_list")
    else:
        form = SparePartForm()
    return render(
        request,
        "inventory/add_part.html",
        {"form": form, "user_role": "admin"},
    )


@login_required(login_url="login")
def edit_part(request, pk):
    """Admin edit part view."""
    part = get_object_or_404(SparePart, pk=pk)
    if request.method == "POST":
        form = SparePartForm(request.POST, instance=part)
        if form.is_valid():
            form.save()
            return redirect("spare_parts_list")
    else:
        form = SparePartForm(instance=part)
    return render(
        request,
        "inventory/edit_part.html",
        {"form": form, "part": part, "user_role": "admin"},
    )


@login_required(login_url="login")
def delete_part(request, pk):
    """Admin delete part view."""
    part = get_object_or_404(SparePart, pk=pk)
    if request.method == "POST":
        part.delete()
        return redirect("spare_parts_list")
    return render(
        request,
        "inventory/delete_part.html",
        {"part": part, "user_role": "admin"},
    )


@login_required(login_url="login")
def edit_employee(request, user_id):
    """Admin view to edit an employee's User and UserProfile."""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("employee_dashboard")

    employee = get_object_or_404(User, id=user_id)
    profile = getattr(employee, "userprofile", None)

    if request.method == "POST":
        form = EmployeeUpdateForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            if profile:
                profile.mobile_number = form.cleaned_data.get("mobile_number", "")
                profile.save()
            return redirect("employees_list")
    else:
        initial = (
            {"mobile_number": getattr(profile, "mobile_number", "")} if profile else {}
        )
        form = EmployeeUpdateForm(instance=employee, initial=initial)

    return render(
        request,
        "inventory/edit_employee.html",
        {
            "form": form,
            "employee": employee,
            "user_role": "admin",
        },
    )


@login_required(login_url="login")
@require_POST
def deactivate_employee(request, user_id):
    """Deactivate (soft-delete) an employee account (admin-only)."""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("employee_dashboard")

    employee = get_object_or_404(User, id=user_id)

    if employee.is_superuser:
        return redirect("employees_list")

    employee.is_active = False
    employee.save()

    if hasattr(employee, "userprofile"):
        employee.userprofile.role = "inactive"
        employee.userprofile.save()

    return redirect("employees_list")


@login_required(login_url="login")
def employees_list(request):
    """List all employees (admin-only)."""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("employee_dashboard")

    employees = User.objects.filter(userprofile__role="employee")
    total_employees = employees.count()

    context = {
        "employees": employees,
        "user_role": "admin",
        "total_employees": total_employees,
    }
    return render(request, "inventory/employees_list.html", context)


@login_required(login_url="login")
def suppliers_list(request):
    """List all suppliers (admin-only)."""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("employee_dashboard")

    suppliers = Supplier.objects.all().order_by("name")
    total_suppliers = suppliers.count()

    context = {
        "suppliers": suppliers,
        "user_role": "admin",
        "total_suppliers": total_suppliers,
    }
    return render(request, "inventory/suppliers_list.html", context)


@login_required(login_url="login")
def add_employee(request):
    """Create a new employee account and send credentials by email."""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("employee_dashboard")

    if request.method == "POST":
        form = EmployeeForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]

            if User.objects.filter(username=username).exists():
                form.add_error(
                    "username",
                    "Username already exists. Please choose a different username.",
                )
                return render(
                    request,
                    "inventory/add_employee.html",
                    {"form": form, "user_role": "admin"},
                )

            random_password = str(uuid.uuid4())[:8]

            user = User.objects.create_user(
                username=username,
                email=form.cleaned_data.get("email", ""),
                first_name=form.cleaned_data.get("first_name", ""),
                last_name=form.cleaned_data.get("last_name", ""),
                password=random_password,
                is_staff=False,
                is_superuser=False,
            )

            UserProfile.objects.create(
                user=user,
                role="employee",
                must_change_password=True,
                mobile_number=form.cleaned_data.get("mobile_number", ""),
            )

            subject = "Your PartsTrack login credentials"
            message = (
                f"Hello {user.first_name},\n\n"
                "Your PartsTrack employee account has been created.\n\n"
                "Login URL: https://example.com/login/\n"
                f"Username: {username}\n"
                f"Password: {random_password}\n\n"
                "Please log in and change your password after your first login."
            )
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [form.cleaned_data.get("email")],
                fail_silently=False,
            )

            context = {
                "employee": user,
                "password": random_password,
                "username": username,
                "user_role": "admin",
                "user": request.user,
            }
            return render(request, "inventory/employee_success.html", context)
    else:
        form = EmployeeForm()

    return render(
        request,
        "inventory/add_employee.html",
        {"form": form, "user_role": "admin"},
    )


@login_required(login_url="login")
def force_password_change(request):
    """Require the logged in user to change their password."""
    user = request.user
    profile = UserProfile.objects.get(user=user)

    if request.method == "POST":
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if not new_password or not confirm_password:
            return render(
                request,
                "inventory/force_password_change.html",
                {"error": "Please fill in both fields."},
            )

        if new_password != confirm_password:
            return render(
                request,
                "inventory/force_password_change.html",
                {"error": "Passwords do not match."},
            )

        user.set_password(new_password)
        user.save()
        profile.must_change_password = False
        profile.save()

        logout(request)
        return redirect("login")

    return render(request, "inventory/force_password_change.html")


@login_required(login_url="login")
def purchase_list(request):  # pylint: disable=unused-argument
    """Render or export a CSV purchase list for parts under minimum stock."""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("employee_dashboard")

    parts = SparePart.objects.filter(
        models.Q(quantity__lte=models.F("minimum_stock"))
        | models.Q(quantity=0),
    )

    if request.method == "POST":
        response = HttpResponse(
            content_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="purchase_list.csv"',
            },
        )
        writer = csv.writer(response)
        writer.writerow(["Part Number", "Part Name", "Quantity To Purchase"])

        for part in parts:
            field_name = f"qty_{part.id}"
            qty_to_buy = request.POST.get(field_name, "").strip()
            if qty_to_buy:
                writer.writerow(
                    [part.part_number, part.part_name, qty_to_buy],
                )

        return response

    return render(
        request,
        "inventory/purchase_list.html",
        {"parts": parts, "user_role": "admin"},
    )
