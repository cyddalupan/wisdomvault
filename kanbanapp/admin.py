from django.contrib import admin
from .models import Board, Column, Task, TaskForm
from django.utils.html import format_html
from django import forms

class TaskAdmin(admin.ModelAdmin):
    form = TaskForm
    list_display = ('title', 'column', 'created_at')
    list_filter = ('column',)
    ordering = ('column',)
    readonly_fields = ('user',)


    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.request = request  # Pass the request to the form
        return form

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

class ColumnForm(forms.ModelForm):
    class Meta:
        model = Column
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        # Pop the request out of kwargs so it doesn't interfere with the superclass __init__
        self.request = kwargs.pop('request', None)
        super(ColumnForm, self).__init__(*args, **kwargs)

        if self.request:
            # Ensure that only the boards created by the current user are visible
            self.fields['board'].queryset = Board.objects.filter(user=self.request.user)

class ColumnAdmin(admin.ModelAdmin):
    list_display = ('name', 'board')
    readonly_fields = ('user',) 

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'board':
            # Filter the queryset for the board field to only include boards owned by the current user
            kwargs['queryset'] = Board.objects.filter(user=request.user)
        return super(ColumnAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super(ColumnAdmin, self).get_queryset(request)
        return qs.filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.user = request.user
        super(ColumnAdmin, self).save_model(request, obj, form, change)

admin.site.register(Column, ColumnAdmin)
admin.site.register(Board, BoardAdmin)
admin.site.register(Task, TaskAdmin)