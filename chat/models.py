from django.db import models

class UserProfile(models.Model):
    facebook_id = models.CharField(max_length=100, unique=True)
    page_id = models.CharField(max_length=100)
    full_name = models.CharField(max_length=255)
    age = models.CharField(null=True, blank=True, max_length=30)
    contact_number = models.CharField(max_length=20, null=True, blank=True)
    whatsapp_number = models.CharField(max_length=20, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    is_copied = models.BooleanField(default=False)

    def __str__(self):
        return self.full_name


class Chat(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    message = models.TextField()
    reply = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat with {self.user.full_name} on {self.timestamp}"