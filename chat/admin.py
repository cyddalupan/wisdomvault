from django.contrib import admin
from .models import UserProfile, Chat, Help

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'facebook_id', 'page_id', 'user_type', 'task')
    search_fields = ('name', 'facebook_id', 'page_id', 'task')
    list_filter = ('task', 'user_type')
    ordering = ('name', 'user_type')

    def user_full_name(self, obj):
        # Check if the user field is not None
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}"
        # Return a default value or an empty string if user is None
        return "No User"

    user_full_name.short_description = 'Full Name'

admin.site.register(UserProfile, UserProfileAdmin)

@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('get_user_name', 'message', 'reply', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('user__name', 'message', 'reply')

    @admin.display(description='User Name')
    def get_user_name(self, obj):
        return obj.user.name if obj.user else "No Name"

@admin.register(Help)
class HelpAdmin(admin.ModelAdmin):
    list_display = ('page_id', 'fb_id', 'name', 'question', 'answer')
    search_fields = ('page_id', 'fb_id', 'name', 'question')