from django.contrib import admin
from .models import UserProfile, Chat

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('facebook_id', 'page_id',  'full_name')
    search_fields = ('facebook_id', 'page_id',  'full_name')

@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'reply', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('user__full_name', 'message', 'reply')