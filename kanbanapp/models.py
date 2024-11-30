from django.db import models
from django import forms

class Board(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Column(models.Model):
    name = models.CharField(max_length=100)
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='columns')
    position = models.IntegerField()

    def __str__(self):
        return self.name

class Task(models.Model):
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
        super(TaskForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Existing task: filter columns by the current task's board
            board = self.instance.column.board
            self.fields['column'].queryset = Column.objects.filter(board=board)
        else:
            # New task: show all columns but display as "Column Name - Board Name"
            self.fields['column'].queryset = Column.objects.select_related('board')
            self.fields['column'].label_from_instance = lambda obj: f"{obj.name} - {obj.board.name}"