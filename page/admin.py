from django.contrib import admin
from .models import FacebookPage

@admin.register(FacebookPage)
class FacebookPageAdmin(admin.ModelAdmin):
    list_display = ('page_id', 'page_name', 'sheet_id', "is_inventory", "is_pos", "is_leads", "is_scheduling", "is_online_selling")
    search_fields = ('page_name', 'page_id', "is_inventory", "is_pos", "is_leads", "is_scheduling", "is_online_selling")
    list_filter = ('page_name',)
    fields = ('page_id', 'page_name', 'token', 'sheet_id', 'info', 'additional_info', "is_inventory", "is_pos", "is_leads", "is_scheduling", "is_online_selling")