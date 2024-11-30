from django.contrib import admin
from .models import Board, Column, Task, TaskForm
from django.utils.html import format_html

class TaskAdmin(admin.ModelAdmin):
    form = TaskForm
    list_display = ('title', 'column', 'created_at')
    list_filter = ('column',)
    ordering = ('column',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Ensure that only tasks related to the requesting user are returned
        return qs.filter(user=request.user)

    def changelist_view(self, request, extra_context=None):
        # Filter boards by user and closed status
        boards = Board.objects.filter(user=request.user, closed=False)
        # Filter columns by user, board and closed status, ensuring columns belong to user's boards
        columns = Column.objects.filter(user=request.user, board__in=boards)
        # Filter tasks in a similar manner, using the columns from above
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

class BoardAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_open')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Ensure that only boards related to the requesting user are returned
        return qs.filter(user=request.user)

    def is_open(self, obj):
        if not obj.closed:
            return format_html('<span style="color: green;">✔ Open</span>')
        else:
            return format_html('<span style="color: red;">✖ Closed</span>')

    is_open.short_description = 'Status'

class ColumnAdmin(admin.ModelAdmin):
    list_display = ('name', 'board')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Ensure that only columns related to user's boards are returned
        return qs.filter(user=request.user)

admin.site.register(Column, ColumnAdmin)
admin.site.register(Board, BoardAdmin)
admin.site.register(Task, TaskAdmin)