from django.contrib import admin
from .models import Note

@admin.register(Note) 
class NoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'updated_at')
    search_fields = ('title', 'content')
    ordering = ('-created_at',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Filter only QuestionAnswer objects created by current user
        return qs.filter(created_by=request.user)