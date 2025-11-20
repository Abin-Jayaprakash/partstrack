from django.apps import AppConfig

class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory'
    
    def ready(self):
        """Configure admin site when apps are ready"""
        from django.contrib import admin
        
        # Admin Site Customization
        admin.site.site_header = "PartsTrack Administration"
        admin.site.site_title = "PartsTrack Admin Portal"
        admin.site.index_title = "Welcome to PartsTrack Admin Dashboard"
