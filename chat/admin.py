from django.contrib import admin
from .models import UserProfile, Chat

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user_full_name', 'facebook_id', 'page_id', 'user_type', 'task')
    search_fields = ('user__first_name', 'user__last_name', 'facebook_id', 'page_id', 'task')
    list_filter = ('task', 'user_type')
    ordering = ('user__first_name', 'user__last_name', 'user_type')

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
    list_display = ('user', 'message', 'reply', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('user__user__first_name', 'user__user__last_name', 'message', 'reply')