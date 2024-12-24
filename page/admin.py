from django.contrib import admin
from .models import FacebookPage

@admin.register(FacebookPage)
class FacebookPageAdmin(admin.ModelAdmin):
    list_display = ('page_id', 'agency_name')
    search_fields = ('agency_name', 'page_id')
    list_filter = ('agency_name',)