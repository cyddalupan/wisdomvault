from django.db import models
import mistune
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User

class DigitalMarketing(models.Model):
    user_input = models.TextField()
    ai_response = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def formatted_output(self):
        markdown = mistune.create_markdown(renderer=mistune.HTMLRenderer())
        html = markdown(self.ai_response)
        return mark_safe(html)
    
    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"GrammarCheck {self.id}"


class Course(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Lesson(models.Model):
    course = models.ForeignKey(Course, related_name='lessons', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    order = models.PositiveIntegerField()
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['order']  # Automatically orders lessons by their 'order' field.

    def __str__(self):
        return f"{self.name} (Course: {self.course.name})"


class LessonProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ('user', 'lesson')  # Prevent duplicate progress entries for the same lesson.
        ordering = ['completed_at']  # Optional: Order progress by completion time.

    def __str__(self):
        return f"Lesson Progress: {self.user.username} - {self.lesson.name} ({'Completed' if self.completed else 'In Progress'})"


class ChatHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey('Lesson', on_delete=models.CASCADE)  # Updated here
    message = models.TextField()
    reply = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Chat by {self.user.username} on {self.lesson.name} at {self.timestamp}"