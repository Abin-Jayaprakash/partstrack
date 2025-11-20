from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.utils import timezone
from .models import SparePart, UserProfile, Sale
from .forms import SparePartForm, EmployeeForm
import uuid
import json

# HOME - REDIRECT TO LOGIN
def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')

# LOGIN VIEW - WITH EMAIL/USERNAME SUPPORT & AUTO ADMIN DETECTION
def custom_login(request):
    if request.method == 'POST':
        username_or_email = request.POST.get('username')
        password = request.POST.get('password')
        
        # Try to authenticate with username first
        user = authenticate(request, username=username_or_email, password=password)
        
        # If not found, try with email
        if user is None:
            try:
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None
        
        if user is not None:
            # Check if user is staff/admin - auto create UserProfile if missing (ONLY at login)
            if user.is_staff or user.is_superuser:
                # Try to get existing profile, if not create one with admin role
                profile, created = UserProfile.objects.get_or_create(user=user)
                if created or profile.role != 'admin':
                    profile.role = 'admin'
                    profile.save()
            else:
                # For non-staff users, ensure they have employee role
                profile, created = UserProfile.objects.get_or_create(user=user)
                if created or profile.role != 'employee':
                    profile.role = 'employee'
                    profile.save()
            
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'inventory/login.html', {'error': 'Invalid username/email or password'})
    return render(request, 'inventory/login.html')

# LOGOUT VIEW
def custom_logout(request):
    logout(request)
    return redirect('login')

# DASHBOARD VIEW - MAIN ENTRY POINT (ROUTES TO CORRECT DASHBOARD)
@login_required(login_url='login')
def dashboard(request):
    # Determine role ONLY based on Django's is_staff/is_superuser
    print(f"[DEBUG] dashboard() - User={request.user.username}, is_staff={request.user.is_staff}")
    
    if request.user.is_staff or request.user.is_superuser:
        # ADMIN - Route to admin dashboard
        print(f"[DEBUG] dashboard() - Redirecting {request.user.username} to admin_dashboard")
        return redirect('admin_dashboard')
    else:
        # EMPLOYEE - Route to employee dashboard
        print(f"[DEBUG] dashboard() - Redirecting {request.user.username} to employee_dashboard")
        return redirect('employee_dashboard')

# ADMIN DASHBOARD VIEW - ADMIN ONLY
@login_required(login_url='login')
def admin_dashboard(request):
    print(f"[DEBUG] admin_dashboard() - User={request.user.username}")
    
    # VERIFY ADMIN - Redirect if employee tries to access
    if not (request.user.is_staff or request.user.is_superuser):
        print(f"[DEBUG] admin_dashboard() - User {request.user.username} is not admin, redirecting to employee_dashboard")
        return redirect('employee_dashboard')
    
    # Set role based on is_staff (DO NOT update UserProfile here)
    user_role = 'admin'
    
    # ADMIN DASHBOARD DATA
    parts = SparePart.objects.all()
    low_stock_parts = parts.filter(quantity__lte=models.F('minimum_stock'))
    out_of_stock_parts = parts.filter(quantity=0)
    
    # Calculate totals
    total_parts = parts.count()
    low_stock_count = low_stock_parts.count()
    out_of_stock_count = out_of_stock_parts.count()
    stock_value = sum(p.quantity * p.price for p in parts)
    sales_count = Sale.objects.count()
    sales_revenue = sum(s.total_price for s in Sale.objects.all())
    
    # Stock status for pie chart
    in_stock = parts.filter(quantity__gt=models.F('minimum_stock')).count()
    
    context = {
        'parts': parts,
        'user_role': user_role,
        'total_parts': total_parts,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'stock_value': f"{stock_value:.2f}",
        'sales_count': sales_count,
        'sales_revenue': f"{sales_revenue:.2f}",
        'low_stock_alerts': low_stock_parts[:5],
        'in_stock': in_stock,
    }
    return render(request, 'inventory/admin_dashboard.html', context)

# EMPLOYEE DASHBOARD VIEW - EMPLOYEE ONLY
@login_required(login_url='login')
def employee_dashboard(request):
    print(f"[DEBUG] employee_dashboard() - User={request.user.username}")
    
    # VERIFY EMPLOYEE - Redirect if admin tries to access
    if request.user.is_staff or request.user.is_superuser:
        print(f"[DEBUG] employee_dashboard() - User {request.user.username} is admin, redirecting to admin_dashboard")
        return redirect('admin_dashboard')
    
    # Set role based on is_staff (DO NOT update UserProfile here)
    user_role = 'employee'
    
    # EMPLOYEE DASHBOARD DATA
    parts = SparePart.objects.all()
    low_stock_parts = parts.filter(quantity__lte=models.F('minimum_stock'))
    
    # Stock status for initial render
    in_stock = parts.filter(quantity__gt=models.F('minimum_stock')).count()
    out_of_stock = parts.filter(quantity=0).count()
    
    # Calculate totals
    total_parts = parts.count()
    low_stock_count = low_stock_parts.count()
    
    # Get sales info
    sales = Sale.objects.all()
    total_sales = sales.count()
    total_revenue = sum(s.total_price for s in sales)
    
    context = {
        'user_role': user_role,
        'total_parts': total_parts,
        'low_stock_count': low_stock_count,
        'in_stock': in_stock,
        'out_of_stock': out_of_stock,
        'total_sales': total_sales,
        'total_revenue': f"{total_revenue:.2f}",
        'low_stock_alerts': low_stock_parts[:5],
    }
    return render(request, 'inventory/employee_dashboard.html', context)

# API - Get Stock Status Data for Chart (AJAX)
@login_required(login_url='login')
def get_stock_status_data(request):
    """API endpoint to get stock status data for chart refresh"""
    parts = SparePart.objects.all()
    
    # Stock Status Distribution
    in_stock = parts.filter(quantity__gt=models.F('minimum_stock')).count()
    low_stock = parts.filter(quantity__lte=models.F('minimum_stock'), quantity__gt=0).count()
    out_of_stock = parts.filter(quantity=0).count()
    
    data = {
        'in_stock': in_stock,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'total': in_stock + low_stock + out_of_stock,
        'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
        'success': True
    }
    
    return JsonResponse(data)

# API - Get Top Selling Parts Data (AJAX)
@login_required(login_url='login')
def get_top_parts_data(request):
    """API endpoint to get top parts data for chart refresh - Real time sync with database"""
    parts = SparePart.objects.all().order_by('-quantity')[:5]
    
    data = {
        'labels': [p.part_name for p in parts],
        'quantities': [p.quantity for p in parts],
        'categories': [p.category for p in parts],
        'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
        'success': True
    }
    
    return JsonResponse(data)

# EMPLOYEE PARTS LIST - WITHOUT PROFILE UPDATE
@login_required(login_url='login')
def employee_parts_list(request):
    print(f"[DEBUG] employee_parts_list() - User={request.user.username}, is_staff={request.user.is_staff}")
    
    # Verify user is employee - redirect admin to admin parts list
    if request.user.is_staff or request.user.is_superuser:
        print(f"[DEBUG] employee_parts_list() - User {request.user.username} is admin, redirecting to spare_parts_list")
        return redirect('spare_parts_list')
    
    user_role = 'employee'
    
    # Get all parts - with CRUD access
    parts = SparePart.objects.all()
    low_stock_parts = parts.filter(quantity__lte=models.F('minimum_stock'))
    out_of_stock_parts = parts.filter(quantity=0)
    
    # Calculate totals
    total_parts = parts.count()
    low_stock_count = low_stock_parts.count()
    out_of_stock_count = out_of_stock_parts.count()
    stock_value = sum(p.quantity * p.price for p in parts)
    
    context = {
        'parts': parts,
        'user_role': user_role,
        'total_parts': total_parts,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'stock_value': f"{stock_value:.2f}",
        'low_stock_alerts': low_stock_parts[:5],
        'is_employee': True,
    }
    return render(request, 'inventory/employee_parts_list.html', context)

# EMPLOYEE ADD PART - CREATE (REDIRECTS TO EMPLOYEE PARTS LIST)
@login_required(login_url='login')
def employee_add_part(request):
    print(f"[DEBUG] employee_add_part() - User={request.user.username}, is_staff={request.user.is_staff}, method={request.method}")
    
    # Verify user is employee - redirect admin
    if request.user.is_staff or request.user.is_superuser:
        print(f"[DEBUG] employee_add_part() - User {request.user.username} is admin, redirecting to add_part")
        return redirect('add_part')
    
    user_role = 'employee'
    
    # Employee can add parts
    if request.method == 'POST':
        form = SparePartForm(request.POST)
        if form.is_valid():
            print(f"[DEBUG] employee_add_part() - Form valid for user {request.user.username}, saving part")
            form.save()
            print(f"[DEBUG] employee_add_part() - Part saved, redirecting {request.user.username} to employee_parts_list")
            # ✅ REDIRECT TO EMPLOYEE PARTS LIST (NOT spare_parts_list)
            return redirect('employee_parts_list')
        else:
            print(f"[DEBUG] employee_add_part() - Form invalid: {form.errors}")
    else:
        form = SparePartForm()
    
    context = {
        'form': form,
        'user_role': user_role,
    }
    return render(request, 'inventory/employee_add_part.html', context)

# EMPLOYEE EDIT PART - UPDATE (REDIRECTS TO EMPLOYEE PARTS LIST)
@login_required(login_url='login')
def employee_edit_part(request, pk):
    print(f"[DEBUG] employee_edit_part() - User={request.user.username}, pk={pk}, method={request.method}")
    
    # Verify user is employee - redirect admin
    if request.user.is_staff or request.user.is_superuser:
        print(f"[DEBUG] employee_edit_part() - User {request.user.username} is admin, redirecting to edit_part")
        return redirect('edit_part', pk=pk)
    
    user_role = 'employee'
    
    # Employee can edit parts
    part = get_object_or_404(SparePart, pk=pk)
    if request.method == 'POST':
        form = SparePartForm(request.POST, instance=part)
        if form.is_valid():
            print(f"[DEBUG] employee_edit_part() - Form valid, saving part {pk}")
            form.save()
            print(f"[DEBUG] employee_edit_part() - Part {pk} updated, redirecting to employee_parts_list")
            # ✅ REDIRECT TO EMPLOYEE PARTS LIST (NOT spare_parts_list)
            return redirect('employee_parts_list')
        else:
            print(f"[DEBUG] employee_edit_part() - Form invalid: {form.errors}")
    else:
        form = SparePartForm(instance=part)
    
    context = {
        'form': form,
        'part': part,
        'user_role': user_role,
    }
    return render(request, 'inventory/employee_edit_part.html', context)

# EMPLOYEE DELETE PART - DELETE (REDIRECTS TO EMPLOYEE PARTS LIST)
@login_required(login_url='login')
def employee_delete_part(request, pk):
    print(f"[DEBUG] employee_delete_part() - User={request.user.username}, pk={pk}, method={request.method}")
    
    # Verify user is employee - redirect admin
    if request.user.is_staff or request.user.is_superuser:
        print(f"[DEBUG] employee_delete_part() - User {request.user.username} is admin, redirecting to delete_part")
        return redirect('delete_part', pk=pk)
    
    user_role = 'employee'
    
    # Employee can delete parts
    part = get_object_or_404(SparePart, pk=pk)
    if request.method == 'POST':
        print(f"[DEBUG] employee_delete_part() - Deleting part {pk}")
        part.delete()
        print(f"[DEBUG] employee_delete_part() - Part {pk} deleted, redirecting to employee_parts_list")
        # ✅ REDIRECT TO EMPLOYEE PARTS LIST (NOT spare_parts_list)
        return redirect('employee_parts_list')
    
    context = {
        'part': part,
        'user_role': user_role,
    }
    return render(request, 'inventory/employee_delete_part.html', context)

# EMPLOYEE ANALYTICS - WITHOUT PROFILE UPDATE
@login_required(login_url='login')
def employee_analytics(request):
    # Verify user is employee
    if request.user.is_staff or request.user.is_superuser:
        return redirect('admin_analytics')
    
    user_role = 'employee'
    
    # Get all parts
    parts = SparePart.objects.all()
    
    # Stock Status Distribution (for Pie Chart)
    in_stock = parts.filter(quantity__gt=models.F('minimum_stock')).count()
    low_stock = parts.filter(quantity__lte=models.F('minimum_stock'), quantity__gt=0).count()
    out_of_stock = parts.filter(quantity=0).count()
    
    # Top 5 Parts by Quantity (for Bar Chart)
    top_parts = parts.order_by('-quantity')[:5]
    top_parts_data = {
        'labels': [p.part_name for p in top_parts],
        'quantities': [p.quantity for p in top_parts],
    }
    
    # Category Distribution (for Donut Chart)
    categories = parts.values('category').annotate(count=models.Count('id'))
    category_data = {
        'labels': [c['category'] for c in categories],
        'counts': [c['count'] for c in categories],
    }
    
    # Stock Value by Category
    category_value = parts.values('category').annotate(
        total_value=models.Sum(models.F('quantity') * models.F('price'), output_field=models.DecimalField())
    ).order_by('-total_value')
    
    # Calculate Analytics Metrics
    total_parts = parts.count()
    total_quantity = sum(p.quantity for p in parts)
    total_stock_value = sum(p.quantity * p.price for p in parts)
    avg_stock_per_part = total_quantity / total_parts if total_parts > 0 else 0
    
    context = {
        'user_role': user_role,
        # Stock Status
        'in_stock': in_stock,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'total_parts': total_parts,
        # Charts Data (JSON)
        'top_parts_json': json.dumps(top_parts_data),
        'category_data_json': json.dumps(category_data),
        # Metrics
        'total_quantity': total_quantity,
        'total_stock_value': f"{total_stock_value:.2f}",
        'avg_stock_per_part': f"{avg_stock_per_part:.2f}",
        # Category Value
        'category_value': category_value,
    }
    return render(request, 'inventory/employee_analytics.html', context)

# ADMIN ANALYTICS - WITHOUT PROFILE UPDATE
@login_required(login_url='login')
def admin_analytics(request):
    """Analytics dashboard for admin users"""
    # Verify user is admin - redirect employees
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('employee_analytics')
    
    user_role = 'admin'
    
    # Get all parts
    parts = SparePart.objects.all()
    
    # Stock Status Distribution (for Pie Chart)
    in_stock = parts.filter(quantity__gt=models.F('minimum_stock')).count()
    low_stock = parts.filter(quantity__lte=models.F('minimum_stock'), quantity__gt=0).count()
    out_of_stock = parts.filter(quantity=0).count()
    
    # Calculate totals
    total_parts = parts.count()
    low_stock_count = low_stock
    
    # Get sales info
    sales = Sale.objects.all()
    total_sales = sales.count()
    total_revenue = sum(s.total_price for s in sales)
    
    context = {
        'user_role': user_role,
        'total_parts': total_parts,
        'low_stock_count': low_stock_count,
        'in_stock': in_stock,
        'out_of_stock': out_of_stock,
        'total_sales': total_sales,
        'total_revenue': f"{total_revenue:.2f}",
        'low_stock_alerts': parts.filter(quantity__lte=models.F('minimum_stock'))[:5],
    }
    return render(request, 'inventory/admin_analytics.html', context)

# SPARE PARTS LIST - WITHOUT PROFILE UPDATE
@login_required(login_url='login')
def spare_parts_list(request):
    # Determine role ONLY from is_staff (not UserProfile)
    if request.user.is_staff or request.user.is_superuser:
        user_role = 'admin'
    else:
        user_role = 'employee'
    
    # All users can view parts
    parts = SparePart.objects.all()
    low_stock_parts = parts.filter(quantity__lte=models.F('minimum_stock'))
    out_of_stock_parts = parts.filter(quantity=0)
    
    # Calculate totals
    total_parts = parts.count()
    low_stock_count = low_stock_parts.count()
    out_of_stock_count = out_of_stock_parts.count()
    stock_value = sum(p.quantity * p.price for p in parts)
    
    context = {
        'parts': parts,
        'user_role': user_role,
        'total_parts': total_parts,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'stock_value': f"{stock_value:.2f}",
        'low_stock_alerts': low_stock_parts[:5],
    }
    return render(request, 'inventory/parts_list.html', context)

# ADD PART VIEW - WITHOUT PROFILE UPDATE
@login_required(login_url='login')
def add_part(request):
    # Determine role ONLY from is_staff
    if request.user.is_staff or request.user.is_superuser:
        user_role = 'admin'
    else:
        user_role = 'employee'
    
    if request.method == 'POST':
        form = SparePartForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('spare_parts_list')
    else:
        form = SparePartForm()
    return render(request, 'inventory/add_part.html', {'form': form, 'user_role': user_role})

# EDIT PART VIEW - WITHOUT PROFILE UPDATE
@login_required(login_url='login')
def edit_part(request, pk):
    # Determine role ONLY from is_staff
    if request.user.is_staff or request.user.is_superuser:
        user_role = 'admin'
    else:
        user_role = 'employee'
    
    part = get_object_or_404(SparePart, pk=pk)
    if request.method == 'POST':
        form = SparePartForm(request.POST, instance=part)
        if form.is_valid():
            form.save()
            return redirect('spare_parts_list')
    else:
        form = SparePartForm(instance=part)
    return render(request, 'inventory/edit_part.html', {'form': form, 'part': part, 'user_role': user_role})

# DELETE PART VIEW - WITHOUT PROFILE UPDATE
@login_required(login_url='login')
def delete_part(request, pk):
    # Determine role ONLY from is_staff
    if request.user.is_staff or request.user.is_superuser:
        user_role = 'admin'
    else:
        user_role = 'employee'
    
    part = get_object_or_404(SparePart, pk=pk)
    if request.method == 'POST':
        part.delete()
        return redirect('spare_parts_list')
    return render(request, 'inventory/delete_part.html', {'part': part, 'user_role': user_role})

# EMPLOYEES LIST - WITHOUT PROFILE UPDATE
@login_required(login_url='login')
def employees_list(request):
    # Verify user is admin
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('employee_dashboard')
    
    user_role = 'admin'
    
    # Get all employees
    employees = User.objects.filter(userprofile__role='employee')
    total_employees = employees.count()
    
    context = {
        'employees': employees,
        'user_role': user_role,
        'total_employees': total_employees,
    }
    return render(request, 'inventory/employees_list.html', context)

# SALES LIST - WITHOUT PROFILE UPDATE
@login_required(login_url='login')
def sales_list(request):
    # Verify user is admin
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('employee_dashboard')
    
    user_role = 'admin'
    
    # Get all sales
    sales = Sale.objects.all()
    total_sales = sales.count()
    total_revenue = sum(s.total_price for s in sales)
    
    context = {
        'sales': sales,
        'user_role': user_role,
        'total_sales': total_sales,
        'total_revenue': f"{total_revenue:.2f}",
    }
    return render(request, 'inventory/sales_list.html', context)

# ADD EMPLOYEE - WITHOUT PROFILE UPDATE (except when creating new employee)
@login_required(login_url='login')
def add_employee(request):
    # Verify user is admin
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('employee_dashboard')
    
    user_role = 'admin'
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            
            # Check if username already exists
            if User.objects.filter(username=username).exists():
                form.add_error('username', 'Username already exists. Please choose a different username.')
                return render(request, 'inventory/add_employee.html', {'form': form, 'user_role': user_role})
            
            # Generate random password
            random_password = str(uuid.uuid4())[:8]
            
            # Create User - CRITICAL: is_staff=False & is_superuser=False
            user = User.objects.create_user(
                username=username,
                email=form.cleaned_data['email'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                password=random_password,
                is_staff=False,        # CRITICAL: Must be False
                is_superuser=False     # CRITICAL: Must be False
            )
            
            # Create UserProfile with employee role (only for record-keeping)
            user_profile = UserProfile.objects.create(
                user=user,
                role='employee'
            )
            user_profile.mobile_number = form.cleaned_data['mobile_number']
            user_profile.save()
            
            context = {
                'employee': user,
                'password': random_password,
                'username': username,
                'user_role': user_role,
                'user': request.user,
            }
            return render(request, 'inventory/employee_success.html', context)
    else:
        form = EmployeeForm()
    
    return render(request, 'inventory/add_employee.html', {'form': form, 'user_role': user_role})