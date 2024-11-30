from django.contrib import admin
from .models import Board, Column, Task, TaskForm
from django.utils.html import format_html

class TaskAdmin(admin.ModelAdmin):
    form = TaskForm
    list_display = ('title', 'column', 'created_at')
    list_filter = ('column',)
    ordering = ('column',)
    readonly_fields = ('user',)  # Makes the user field read-only

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(user=request.user)

    def changelist_view(self, request, extra_context=None):
        boards = Board.objects.filter(user=request.user, closed=False)
        columns = Column.objects.filter(user=request.user, board__in=boards)
        tasks = self.model.objects.filter(user=request.user, column__in=columns)

        board_data = {
            board: {
                'columns': columns.filter(board=board),
                'column_tasks': {
                    column.name: tasks.filter(column=column)
                    for column in columns.filter(board=board)
                }
            }
            for board in boards
        }

        extra_context = extra_context or {}
        extra_context['board_data'] = board_data

        return super(TaskAdmin, self).changelist_view(request, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Only set user on creation, not on updates
            obj.user = request.user
        super().save_model(request, obj, form, change)

class BoardAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_open')
    readonly_fields = ('user',)  # Makes the user field read-only

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(user=request.user)

    def is_open(self, obj):
        if not obj.closed:
            return format_html('<span style="color: green;">✔ Open</span>')
        else:
            return format_html('<span style="color: red;">✖ Closed</span>')

    is_open.short_description = 'Status'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.user = request.user
        super().save_model(request, obj, form, change)

class ColumnAdmin(admin.ModelAdmin):
    list_display = ('name', 'board')
    readonly_fields = ('user',)  # Makes the user field read-only

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.user = request.user
        super().save_model(request, obj, form, change)

admin.site.register(Column, ColumnAdmin)
admin.site.register(Board, BoardAdmin)
admin.site.register(Task, TaskAdmin)