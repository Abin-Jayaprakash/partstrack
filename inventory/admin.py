"""Admin configuration for the inventory app."""
from django.contrib import admin
from django.utils.html import format_html
from .models import SparePart, UserProfile, Sale


# SPARE PARTS ADMIN
@admin.register(SparePart)
class SparePartAdmin(admin.ModelAdmin):
    """Admin configuration for SparePart with advanced search and filters."""
    list_display = (
        'part_name',
        'category',
        'quantity',
        'minimum_stock',
        'stock_status_badge',
        'price',
        'supplier',
    )
    list_filter = (
        'category',
        'supplier',
        ('quantity', admin.EmptyFieldListFilter),
    )
    search_fields = (
        'part_name',
        'description',
        'category',
        'supplier',
    )
    readonly_fields = ('stock_status_badge',)
    ordering = ('quantity',)  # Default: lowest stock first
    list_per_page = 25

    fieldsets = (
        ('Basic Information', {
            'fields': ('part_name', 'description')
        }),
        ('Stock Information', {
            'fields': ('quantity', 'minimum_stock', 'reorder_quantity',
                      'stock_status_badge')
        }),
        ('Pricing', {
            'fields': ('price',)
        }),
        ('Organization', {
            'fields': ('category', 'supplier')
        }),
    )

    def stock_status_badge(self, obj):
        """Display color-coded stock status badge."""
        if obj.quantity == 0:
            color = '#dc3545'  # Red
            status = 'OUT OF STOCK'
            icon = '🔴'
        elif obj.quantity <= obj.minimum_stock:
            color = '#ffc107'  # Orange
            status = 'LOW STOCK'
            icon = '🟡'
        else:
            color = '#28a745'  # Green
            status = 'IN STOCK'
            icon = '🟢'

        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; '
            'border-radius: 4px; font-weight: bold; display: inline-block;">'
            '{} {}</span>',
            color,
            icon,
            status,
        )

    stock_status_badge.short_description = 'Stock Status'

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        queryset = super().get_queryset(request)
        return queryset.select_related('supplier')


# USER PROFILE ADMIN
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin configuration for UserProfile with advanced search and filters."""
    list_display = (
        'get_username',
        'get_email',
        'role_badge',
        'mobile_number',
        'get_user_status',
    )
    list_filter = (
        'role',
        ('user__is_active', admin.BooleanFieldListFilter),
    )
    search_fields = (
        'user__username',
        'user__email',
        'mobile_number',
        'user__first_name',
        'user__last_name',
    )
    readonly_fields = ('user', 'role_badge')
    ordering = ('user__username',)
    list_per_page = 25

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'mobile_number')
        }),
        ('Role', {
            'fields': ('role', 'role_badge')
        }),
    )

    def get_username(self, obj):
        """Display username from related User."""
        return obj.user.username

    get_username.short_description = 'Username'

    def get_email(self, obj):
        """Display email from related User."""
        return obj.user.email

    get_email.short_description = 'Email'

    def get_user_status(self, obj):
        """Display user active status."""
        if obj.user.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Active</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗ Inactive</span>'
        )

    get_user_status.short_description = 'Status'

    def role_badge(self, obj):
        """Display role as a colored badge."""
        colors = {
            'admin': '#007bff',
            'employee': '#28a745',
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            (
                '<span style="background-color: {}; color: white; '
                'padding: 5px 10px; border-radius: 4px; font-weight: bold; '
                'display: inline-block;">{}</span>'
            ),
            color,
            obj.role.upper(),
        )

    role_badge.short_description = 'Role'

    def has_add_permission(self, request):
        """Only admins can add user profiles."""
        return request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        """Only admins can delete user profiles."""
        return request.user.is_staff


# SALE ADMIN
@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    """Admin configuration for Sale with advanced search and filters."""
    list_display = (
        'get_sale_id',
        'part',
        'quantity_sold',
        'total_price',
        'sale_status_badge',
    )
    list_filter = (
        'part__category',
        'part',
        ('quantity_sold', admin.EmptyFieldListFilter),
    )
    search_fields = (
        'part__part_name',
        'id',
    )
    readonly_fields = (
        'get_sale_id',
        'sale_status_badge',
    )
    ordering = ('-id',)  # Latest sales first
    list_per_page = 25

    fieldsets = (
        ('Sale Information', {
            'fields': ('get_sale_id', 'part', 'quantity_sold')
        }),
        ('Pricing', {
            'fields': ('total_price',)
        }),
        ('Status', {
            'fields': ('sale_status_badge',),
            'classes': ('wide',)
        }),
    )

    def get_sale_id(self, obj):
        """Display sale ID."""
        return f"SALE-{obj.id}" if obj.id else 'N/A'

    get_sale_id.short_description = 'Sale ID'

    def sale_status_badge(self, obj):
        """Display sale completion status."""
        return format_html(
            '<span style="background-color: #28a745; color: white; '
            'padding: 5px 10px; border-radius: 4px; font-weight: bold; '
            'display: inline-block;">✓ Completed</span>'
        )

    sale_status_badge.short_description = 'Status'

    def has_add_permission(self, request):
        """Only admins can add sales."""
        return request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        """Only admins can delete sales."""
        return request.user.is_staff

    def has_change_permission(self, request, obj=None):
        """Only admins can edit sales."""
        return request.user.is_staff

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        queryset = super().get_queryset(request)
        return queryset.select_related('part')
