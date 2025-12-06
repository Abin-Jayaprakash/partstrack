"""App configuration for the inventory app."""
from django.apps import AppConfig
from django.contrib import admin


class InventoryConfig(AppConfig):
    """Django app configuration for the inventory app."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventory"

    def ready(self):
        """Configure admin site when apps are ready."""
        admin.site.site_header = "PartsTrack Administration"
        admin.site.site_title = "PartsTrack Admin Portal"
        admin.site.index_title = "Welcome to PartsTrack Admin Dashboard"
