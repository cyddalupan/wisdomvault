from django.contrib.auth.models import User
from django.db import models

class UserProfile(models.Model):
    facebook_id = models.CharField(max_length=100, unique=True)
    page_id = models.CharField(max_length=100)
    name = models.CharField(max_length=255, null=True)
    user_type = models.CharField(max_length=255)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    task = models.CharField(max_length=255, default='', blank=True)
    summary = models.TextField(blank=True, null=True)
    is_leads_complete = models.BooleanField(default=False)

    def __str__(self):
        if self.name:
            return self.name
        return "No Name"

class Chat(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    message = models.TextField()
    reply = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_summarized = models.BooleanField(default=False)

    def __str__(self):
        if self.user and self.user.user:
            return f"Chat with {self.user.user.first_name} {self.user.user.last_name} on {self.timestamp}"
        return f"Chat on {self.timestamp}"

class Help(models.Model):
    page_id = models.CharField(max_length=255)
    fb_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    question = models.TextField()
    answer = models.TextField(blank=True, null=True) 

    def __str__(self):
        return f"{self.name}: {self.question[:50]}..."