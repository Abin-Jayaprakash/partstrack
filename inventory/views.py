from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Sum, Count
from django.views.decorators.http import require_POST
from django import forms
from .models import SparePart, UserProfile, Sale
from .forms import SparePartForm, EmployeeForm
import uuid
import json
import csv

# ---------- NEW: EmployeeUpdateForm ----------
class EmployeeUpdateForm(forms.ModelForm):
    mobile_number = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

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
        
        user = authenticate(request, username=username_or_email, password=password)
        
        if user is None:
            try:
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None
        
        if user is not None and user.is_active:
            if user.is_staff or user.is_superuser:
                profile, created = UserProfile.objects.get_or_create(user=user)
                if created or profile.role != 'admin':
                    profile.role = 'admin'
                    profile.save()
            else:
                profile, created = UserProfile.objects.get_or_create(user=user)
                if created or profile.role != 'employee':
                    profile.role = 'employee'
                    profile.save()
            
            login(request, user)

            if hasattr(profile, 'must_change_password') and profile.must_change_password:
                return redirect('force_password_change')

            return redirect('dashboard')
        else:
            return render(request, 'inventory/login.html', {'error': 'Invalid username/email or password'})
    return render(request, 'inventory/login.html')

# LOGOUT VIEW
def custom_logout(request):
    logout(request)
    return redirect('login')

# DASHBOARD VIEW
@login_required(login_url='login')
def dashboard(request):
    print(f"[DEBUG] dashboard() - User={request.user.username}, is_staff={request.user.is_staff}")
    
    if request.user.is_staff or request.user.is_superuser:
        print(f"[DEBUG] dashboard() - Redirecting {request.user.username} to admin_dashboard")
        return redirect('admin_dashboard')
    else:
        print(f"[DEBUG] dashboard() - Redirecting {request.user.username} to employee_dashboard")
        return redirect('employee_dashboard')

# ADMIN DASHBOARD
@login_required(login_url='login')
def admin_dashboard(request):
    print(f"[DEBUG] admin_dashboard() - User={request.user.username}")
    
    if not (request.user.is_staff or request.user.is_superuser):
        print(f"[DEBUG] admin_dashboard() - User {request.user.username} is not admin, redirecting to employee_dashboard")
        return redirect('employee_dashboard')
    
    user_role = 'admin'
    
    parts = SparePart.objects.all()
    low_stock_parts = parts.filter(quantity__lte=models.F('minimum_stock'))
    out_of_stock_parts = parts.filter(quantity=0)
    
    total_parts = parts.count()
    low_stock_count = low_stock_parts.count()
    out_of_stock_count = out_of_stock_parts.count()
    stock_value = sum(p.quantity * p.price for p in parts)
    sales_count = Sale.objects.count()
    sales_revenue = sum(s.total_price for s in Sale.objects.all())
    
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

# EMPLOYEE DASHBOARD
@login_required(login_url='login')
def employee_dashboard(request):
    print(f"[DEBUG] employee_dashboard() - User={request.user.username}")
    
    if request.user.is_staff or request.user.is_superuser:
        print(f"[DEBUG] employee_dashboard() - User {request.user.username} is admin, redirecting to admin_dashboard")
        return redirect('admin_dashboard')
    
    user_role = 'employee'
    
    parts = SparePart.objects.all()
    low_stock_parts = parts.filter(quantity__lte=models.F('minimum_stock'))
    
    in_stock = parts.filter(quantity__gt=models.F('minimum_stock')).count()
    out_of_stock = parts.filter(quantity=0).count()
    
    total_parts = parts.count()
    low_stock_count = low_stock_parts.count()
    
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

# API - Stock Status
@login_required(login_url='login')
def get_stock_status_data(request):
    try:
        parts = SparePart.objects.all()
        
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
        
        print(f"[DEBUG] get_stock_status_data() - Returning: {data}")
        return JsonResponse(data)
    except Exception as e:
        print(f"[ERROR] get_stock_status_data: {str(e)}")
        return JsonResponse({'error': str(e), 'success': False}, status=500)

# API - Top Parts
@login_required(login_url='login')
def get_top_parts_data(request):
    print(f"\n[DEBUG] get_top_parts_data() called")
    
    try:
        sale_count = Sale.objects.count()
        print(f"[DEBUG] Total sales in database: {sale_count}")
        
        if sale_count > 0:
            first_sale = Sale.objects.first()
            print(f"[DEBUG] First sale object: {first_sale}")
            print(f"[DEBUG] First sale __dict__: {first_sale.__dict__}")
        
        try:
            top_parts = Sale.objects.values('part__part_name').annotate(
                total_quantity=Sum('quantity_sold')
            ).order_by('-total_quantity')[:5]
            
            if top_parts.exists():
                labels = [item['part__part_name'] for item in top_parts]
                quantities = [item['total_quantity'] for item in top_parts]
                print(f"[DEBUG] Success with part__part_name - Labels: {labels}")
            else:
                raise ValueError("No data with part__part_name")
                
        except Exception as e1:
            print(f"[DEBUG] Attempt 1 failed: {e1}, using fallback")
            fallback_parts = SparePart.objects.all().order_by('-quantity')[:5]
            labels = [p.part_name for p in fallback_parts]
            quantities = [p.quantity for p in fallback_parts]
            print(f"[DEBUG] Using fallback - Labels: {labels}, Quantities: {quantities}")
        
        data = {
            'labels': labels if labels else ['No data'],
            'quantities': quantities if quantities else [0],
            'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'success': True
        }
        
        print(f"[DEBUG] Final response: {data}\n")
        return JsonResponse(data)
        
    except Exception as e:
        print(f"\n[ERROR] get_top_parts_data: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback:\n{traceback.format_exc()}\n")
        
        return JsonResponse({
            'error': str(e), 
            'labels': ['Error'], 
            'quantities': [0],
            'success': False
        }, status=500)

# EMPLOYEE PARTS LIST
@login_required(login_url='login')
def employee_parts_list(request):
    print(f"[DEBUG] employee_parts_list() - User={request.user.username}, is_staff={request.user.is_staff}")
    
    if request.user.is_staff or request.user.is_superuser:
        print(f"[DEBUG] employee_parts_list() - User {request.user.username} is admin, redirecting to spare_parts_list")
        return redirect('spare_parts_list')
    
    user_role = 'employee'
    
    parts = SparePart.objects.all()
    low_stock_parts = parts.filter(quantity__lte=models.F('minimum_stock'))
    out_of_stock_parts = parts.filter(quantity=0)
    
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

# EMPLOYEE ADD PART
@login_required(login_url='login')
def employee_add_part(request):
    print(f"[DEBUG] employee_add_part() - User={request.user.username}, is_staff={request.user.is_staff}, method={request.method}")
    
    if request.user.is_staff or request.user.is_superuser:
        print(f"[DEBUG] employee_add_part() - User {request.user.username} is admin, redirecting to add_part")
        return redirect('add_part')
    
    user_role = 'employee'
    
    if request.method == 'POST':
        form = SparePartForm(request.POST)
        if form.is_valid():
            print(f"[DEBUG] employee_add_part() - Form valid for user {request.user.username}, saving part")
            form.save()
            print(f"[DEBUG] employee_add_part() - Part saved, redirecting {request.user.username} to employee_parts_list")
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

# EMPLOYEE EDIT PART
@login_required(login_url='login')
def employee_edit_part(request, pk):
    print(f"[DEBUG] employee_edit_part() - User={request.user.username}, pk={pk}, method={request.method}")
    
    if request.user.is_staff or request.user.is_superuser:
        print(f"[DEBUG] employee_edit_part() - User {request.user.username} is admin, redirecting to edit_part")
        return redirect('edit_part', pk=pk)
    
    user_role = 'employee'
    
    part = get_object_or_404(SparePart, pk=pk)
    if request.method == 'POST':
        form = SparePartForm(request.POST, instance=part)
        if form.is_valid():
            print(f"[DEBUG] employee_edit_part() - Form valid, saving part {pk}")
            form.save()
            print(f"[DEBUG] employee_edit_part() - Part {pk} updated, redirecting to employee_parts_list")
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

# EMPLOYEE DELETE PART
@login_required(login_url='login')
def employee_delete_part(request, pk):
    print(f"[DEBUG] employee_delete_part() - User={request.user.username}, pk={pk}, method={request.method}")
    
    if request.user.is_staff or request.user.is_superuser:
        print(f"[DEBUG] employee_delete_part() - User {request.user.username} is admin, redirecting to delete_part")
        return redirect('delete_part', pk=pk)
    
    user_role = 'employee'
    
    part = get_object_or_404(SparePart, pk=pk)
    if request.method == 'POST':
        print(f"[DEBUG] employee_delete_part() - Deleting part {pk}")
        part.delete()
        print(f"[DEBUG] employee_delete_part() - Part {pk} deleted, redirecting to employee_parts_list")
        return redirect('employee_parts_list')
    
    context = {
        'part': part,
        'user_role': user_role,
    }
    return render(request, 'inventory/employee_delete_part.html', context)

# EMPLOYEE ANALYTICS - DISABLED
@login_required(login_url='login')
def employee_analytics(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect('admin_analytics')
    return redirect('employee_dashboard')

# ADMIN ANALYTICS
@login_required(login_url='login')
def admin_analytics(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('employee_dashboard')
    
    user_role = 'admin'
    
    parts = SparePart.objects.all()
    
    in_stock = parts.filter(quantity__gt=models.F('minimum_stock')).count()
    low_stock = parts.filter(quantity__lte=models.F('minimum_stock'), quantity__gt=0).count()
    out_of_stock = parts.filter(quantity=0).count()
    
    total_parts = parts.count()
    low_stock_count = low_stock
    
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

# SPARE PARTS LIST (ADMIN)
@login_required(login_url='login')
def spare_parts_list(request):
    if request.user.is_staff or request.user.is_superuser:
        user_role = 'admin'
    else:
        user_role = 'employee'
    
    parts = SparePart.objects.all()
    low_stock_parts = parts.filter(quantity__lte=models.F('minimum_stock'))
    out_of_stock_parts = parts.filter(quantity=0)
    
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

# ADD PART (ADMIN)
@login_required(login_url='login')
def add_part(request):
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

# EDIT PART (ADMIN)
@login_required(login_url='login')
def edit_part(request, pk):
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

# DELETE PART (ADMIN)
@login_required(login_url='login')
def delete_part(request, pk):
    if request.user.is_staff or request.user.is_superuser:
        user_role = 'admin'
    else:
        user_role = 'employee'
    
    part = get_object_or_404(SparePart, pk=pk)
    if request.method == 'POST':
        part.delete()
        return redirect('spare_parts_list')
    return render(request, 'inventory/delete_part.html', {'part': part, 'user_role': user_role})

# ---------- NEW: EDIT EMPLOYEE ----------
@login_required(login_url='login')
def edit_employee(request, user_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('employee_dashboard')

    employee = get_object_or_404(User, id=user_id)
    profile = employee.userprofile

    if request.method == 'POST':
        form = EmployeeUpdateForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            profile.mobile_number = form.cleaned_data['mobile_number']
            profile.save()
            return redirect('employees_list')
    else:
        form = EmployeeUpdateForm(
            instance=employee,
            initial={'mobile_number': profile.mobile_number}
        )

    return render(
        request,
        'inventory/edit_employee.html',
        {'form': form, 'employee': employee, 'user_role': 'admin'}
    )

# DEACTIVATE EMPLOYEE
@login_required(login_url='login')
@require_POST
def deactivate_employee(request, user_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('employee_dashboard')

    employee = get_object_or_404(User, id=user_id)

    if employee.is_superuser:
        return redirect('employees_list')

    employee.is_active = False
    employee.save()

    if hasattr(employee, 'userprofile'):
        employee.userprofile.role = 'inactive'
        employee.userprofile.save()

    return redirect('employees_list')

# EMPLOYEES LIST
@login_required(login_url='login')
def employees_list(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('employee_dashboard')
    
    user_role = 'admin'
    
    employees = User.objects.filter(userprofile__role='employee')
    total_employees = employees.count()
    
    context = {
        'employees': employees,
        'user_role': user_role,
        'total_employees': total_employees,
    }
    return render(request, 'inventory/employees_list.html', context)

# SALES LIST
@login_required(login_url='login')
def sales_list(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('employee_dashboard')
    
    user_role = 'admin'
    
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

# ADD EMPLOYEE
@login_required(login_url='login')
def add_employee(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('employee_dashboard')
    
    user_role = 'admin'
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            
            if User.objects.filter(username=username).exists():
                form.add_error('username', 'Username already exists. Please choose a different username.')
                return render(request, 'inventory/add_employee.html', {'form': form, 'user_role': user_role})
            
            random_password = str(uuid.uuid4())[:8]
            
            user = User.objects.create_user(
                username=username,
                email=form.cleaned_data['email'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                password=random_password,
                is_staff=False,
                is_superuser=False
            )
            
            user_profile = UserProfile.objects.create(
                user=user,
                role='employee',
                must_change_password=True
            )
            user_profile.mobile_number = form.cleaned_data['mobile_number']
            user_profile.save()

            subject = "Your PartsTrack login credentials"
            message = (
                f"Hello {user.first_name},\n\n"
                f"Your PartsTrack employee account has been created.\n\n"
                f"Login URL: https://cfaaf59d88e441849ad2c53ec6571e4b.vfs.cloud9.us-east-1.amazonaws.com:8080/login/\n"
                f"Username: {username}\n"
                f"Password: {random_password}\n\n"
                f"Please log in and change your password after your first login."
            )
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [form.cleaned_data['email']],
                fail_silently=False,
            )
            
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

# FORCE PASSWORD CHANGE
@login_required(login_url='login')
def force_password_change(request):
    user = request.user
    profile = UserProfile.objects.get(user=user)

    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not new_password or not confirm_password:
            return render(request, 'inventory/force_password_change.html', {
                'error': 'Please fill in both fields.'
            })

        if new_password != confirm_password:
            return render(request, 'inventory/force_password_change.html', {
                'error': 'Passwords do not match.'
            })

        user.set_password(new_password)
        user.save()

        profile.must_change_password = False
        profile.save()

        logout(request)
        return redirect('login')

    return render(request, 'inventory/force_password_change.html')

# PURCHASE LIST VIEW
@login_required(login_url='login')
def purchase_list(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('employee_dashboard')

    parts = SparePart.objects.filter(
        models.Q(quantity__lte=models.F('minimum_stock')) | models.Q(quantity=0)
    )

    if request.method == 'POST':
        response = HttpResponse(
            content_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename="purchase_list.csv"'},
        )
        writer = csv.writer(response)
        writer.writerow(['Part Number', 'Part Name', 'Quantity To Purchase'])

        for part in parts:
            field_name = f"qty_{part.id}"
            qty_to_buy = request.POST.get(field_name, '').strip()
            if qty_to_buy:
                writer.writerow([part.part_number, part.part_name, qty_to_buy])

        return response

    user_role = 'admin'
    context = {
        'parts': parts,
        'user_role': user_role,
    }
    return render(request, 'inventory/purchase_list.html', context)
