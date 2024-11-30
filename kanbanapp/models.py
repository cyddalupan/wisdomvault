from django.db import models
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model

class Board(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='boards')
    name = models.CharField(max_length=100)
    closed = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Column(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='columns')
    name = models.CharField(max_length=100)
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='columns')
    position = models.IntegerField()

    def __str__(self):
        return self.name

class Task(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    column = models.ForeignKey(Column, on_delete=models.CASCADE, related_name='tasks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super(TaskForm, self).__init__(*args, **kwargs)
        
        if request:
            self.fields['column'].queryset = Column.objects.filter(user=request.user, board__closed=False).select_related('board')
        
        if self.instance and self.instance.pk:
            # Existing task: filter columns by the current task's board
            board = self.instance.column.board
            self.fields['column'].queryset = Column.objects.filter(user=request.user, board=board, board__closed=False)