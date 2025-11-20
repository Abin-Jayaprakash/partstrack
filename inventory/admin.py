from django.contrib import admin
from django.utils.html import format_html
from .models import SparePart, UserProfile, Sale

# SPARE PARTS ADMIN
@admin.register(SparePart)
class SparePartAdmin(admin.ModelAdmin):
    list_display = ('part_name', 'category', 'quantity', 'stock_status', 'price', 'supplier')
    list_filter = ('category', 'supplier')
    search_fields = ('part_name', 'description', 'part_code')
    readonly_fields = ('stock_status',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('part_name', 'part_code', 'description')
        }),
        ('Stock Information', {
            'fields': ('quantity', 'minimum_stock', 'reorder_quantity')
        }),
        ('Pricing', {
            'fields': ('price',)
        }),
        ('Organization', {
            'fields': ('category', 'supplier')
        }),
    )
    
    def stock_status(self, obj):
        """Display color-coded stock status"""
        if obj.quantity == 0:
            color = 'red'
            status = 'OUT OF STOCK'
        elif obj.quantity <= obj.minimum_stock:
            color = 'orange'
            status = 'LOW STOCK'
        else:
            color = 'green'
            status = 'IN STOCK'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            status
        )
    stock_status.short_description = 'Stock Status'

# USER PROFILE ADMIN
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('get_username', 'get_email', 'role_badge', 'mobile_number')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email', 'mobile_number')
    readonly_fields = ('user',)
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'mobile_number')
        }),
        ('Role', {
            'fields': ('role',)
        }),
    )
    
    def get_username(self, obj):
        """Display username from related User"""
        return obj.user.username
    get_username.short_description = 'Username'
    
    def get_email(self, obj):
        """Display email from related User"""
        return obj.user.email
    get_email.short_description = 'Email'
    
    def role_badge(self, obj):
        """Display role as a colored badge"""
        colors = {
            'admin': 'blue',
            'employee': 'green'
        }
        color = colors.get(obj.role, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.role.upper()
        )
    role_badge.short_description = 'Role'

# SALE ADMIN
@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('get_sale_id', 'part', 'quantity_sold', 'total_price', 'get_date_sold')
    list_filter = ('part',)
    search_fields = ('part__part_name',)
    readonly_fields = ('get_sale_id', 'get_date_sold')
    
    fieldsets = (
        ('Sale Information', {
            'fields': ('get_sale_id', 'part', 'quantity_sold')
        }),
        ('Pricing', {
            'fields': ('total_price',)
        }),
        ('Date', {
            'fields': ('get_date_sold',),
            'classes': ('collapse',)
        }),
    )
    
    def get_sale_id(self, obj):
        """Display sale ID"""
        return obj.id if obj.id else 'N/A'
    get_sale_id.short_description = 'Sale ID'
    
    def get_date_sold(self, obj):
        """Display date sold"""
        return obj.id  # Placeholder - adjust based on your model
    get_date_sold.short_description = 'Date'
    
    def has_add_permission(self, request):
        """Only admins can add sales"""
        return request.user.is_staff
    
    def has_delete_permission(self, request, obj=None):
        """Only admins can delete sales"""
        return request.user.is_staff