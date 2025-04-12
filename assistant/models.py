from django.contrib.auth.models import User
from django.db import models
import mistune
from django.utils.safestring import mark_safe

class Assistant(models.Model):
    name = models.CharField(max_length=100)
    instruction = models.TextField()

    def __str__(self):
        return self.name

class ChatHistory(models.Model):
    assistant = models.ForeignKey(Assistant, on_delete=models.CASCADE, related_name='chat_histories')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_histories')
    message = models.TextField()
    reply = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} to {self.assistant.name} - {self.message[:50]}"
    
class Tableau(models.Model):
    assistant = models.ForeignKey(Assistant, on_delete=models.CASCADE)
    message = models.TextField()
    reply = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def formatted_output(self):
        markdown = mistune.create_markdown(renderer=mistune.HTMLRenderer())
        html = markdown(self.reply)
        return mark_safe(html)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"Tableau Message {self.id}"