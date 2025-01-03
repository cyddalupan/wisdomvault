from django.contrib import admin
from .models import FacebookPage

@admin.register(FacebookPage)
class FacebookPageAdmin(admin.ModelAdmin):
    list_display = ('page_id', 'page_name', 'sheet_id')
    search_fields = ('page_name', 'page_id')
    list_filter = ('page_name',)
    fields = ('page_id', 'page_name', 'token', 'sheet_id', 'info')