from django.contrib.auth.models import User
from django.db import models

class UserProfile(models.Model):
    facebook_id = models.CharField(max_length=100, unique=True)
    page_id = models.CharField(max_length=100)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, default='')
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    task = models.CharField(max_length=255, default='verify_user')

    def __str__(self):
        return self.full_name


class Chat(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    message = models.TextField()
    reply = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat with {self.user.full_name} on {self.timestamp}"