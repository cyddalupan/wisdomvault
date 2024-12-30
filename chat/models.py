from django.contrib.auth.models import User
from django.db import models

class UserProfile(models.Model):
    facebook_id = models.CharField(max_length=100, unique=True)
    page_id = models.CharField(max_length=100)
    user_type = models.CharField(max_length=255)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    task = models.CharField(max_length=255, default='', blank=True)

    def __str__(self):
        if self.user:
            return f"{self.user.first_name} {self.user.last_name}"
        return "UserProfile with no linked User"

class Chat(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    message = models.TextField()
    reply = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.user and self.user.user:
            return f"Chat with {self.user.user.first_name} {self.user.user.last_name} on {self.timestamp}"
        return f"Chat on {self.timestamp}"