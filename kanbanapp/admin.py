from django.contrib import admin
from django.utils.html import format_html
from .models import Board, Column, Task, TaskForm
from django import forms

class TaskAdmin(admin.ModelAdmin):
    form = TaskForm
    list_display = ('title', 'column', 'created_at')
    list_filter = ('column',)
    ordering = ('column',)
    readonly_fields = ('user',)

    def get_form(self, request, obj=None, **kwargs):
        form_class = self.form

        # Create a subclass to pass the request to the form
        class TaskFormWithRequest(form_class):
            def __init__(inner_self, *args, **inner_kwargs):
                inner_kwargs['request'] = request
                super(TaskFormWithRequest, inner_self).__init__(*args, **inner_kwargs)

        kwargs['form'] = TaskFormWithRequest
        return super().get_form(request, obj, **kwargs)

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
                },
            }
            for board in boards
        }

        extra_context = extra_context or {}
        extra_context['board_data'] = board_data

        return super().changelist_view(request, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.user = request.user
        super().save_model(request, obj, form, change)

class BoardAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_open')
    readonly_fields = ('user',)

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
    readonly_fields = ('user',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'board':
            # Filter the queryset for the board field to only include boards owned by the current user and not closed
            kwargs['queryset'] = Board.objects.filter(user=request.user, closed=False)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.user = request.user
        super().save_model(request, obj, form, change)

admin.site.register(Task, TaskAdmin)
admin.site.register(Board, BoardAdmin)
admin.site.register(Column, ColumnAdmin)