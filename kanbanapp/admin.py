from django.contrib import admin
from .models import Board, Column, Task
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'column', 'created_at')
    list_filter = ('column',)
    ordering = ('column',)

    def changelist_view(self, request, extra_context=None):
        boards = Board.objects.all()
        columns = Column.objects.select_related('board').all()  # Fetch columns with their boards
        tasks = self.model.objects.select_related('column__board').all()  # Fetch tasks with related columns and boards

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

class ColumnAdmin(admin.ModelAdmin):
    list_display = ('name',)

class BoardAdmin(admin.ModelAdmin):
    list_display = ('name',)  # Remove 'created_at' since it's not a field

admin.site.register(Column, ColumnAdmin)
admin.site.register(Board, BoardAdmin)
admin.site.register(Task, TaskAdmin)
