from django.contrib import admin
from .models import Assistant, ChatHistory, Tableau

class AssistantAdmin(admin.ModelAdmin):
    list_display = ('name', 'instruction')
    search_fields = ('name',)

class ChatHistoryAdmin(admin.ModelAdmin):
    list_display = ('assistant', 'user', 'message', 'reply', 'timestamp')
    search_fields = ('message', 'reply')
    list_filter = ('assistant', 'user', 'timestamp')

admin.site.register(Assistant, AssistantAdmin)
admin.site.register(ChatHistory, ChatHistoryAdmin)

class TableauAdmin(admin.ModelAdmin):
    change_list_template = "admin/chat_template.html"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        try:
            assistant = Assistant.objects.get(name="Tableou")
            tableaus = Tableau.objects.filter(assistant=assistant)
        except Assistant.DoesNotExist:
            tableaus = Tableau.objects.none()
        
        extra_context['tableaus'] = tableaus
        return super().changelist_view(request, extra_context=extra_context)

admin.site.register(Tableau, TableauAdmin)