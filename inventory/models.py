from django.db import models
from django.contrib.auth.models import User

# Role choices
ROLE_CHOICES = [
    ('admin', 'Admin'),
    ('employee', 'Employee'),
]

# User Profile Model
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, default='employee', choices=ROLE_CHOICES)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

# Supplier Model
class Supplier(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

# Spare Part Model
class SparePart(models.Model):
    part_number = models.CharField(max_length=100, unique=True)
    part_name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True)
    quantity = models.IntegerField(default=0)
    minimum_stock = models.IntegerField(default=10)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    location = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def is_low_stock(self):
        return self.quantity <= self.minimum_stock
    
    def __str__(self):
        return f"{self.part_number} - {self.part_name}"

# Sales Model
class Sale(models.Model):
    sale_number = models.CharField(max_length=100, unique=True)
    part = models.ForeignKey(SparePart, on_delete=models.CASCADE)
    quantity_sold = models.IntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    employee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    sale_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Sale {self.sale_number}"
