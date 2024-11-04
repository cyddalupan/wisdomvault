from django.db import models

class QuestionAnswer(models.Model):
    title = models.CharField(max_length=255)
    question = models.TextField()
    answer = models.TextField(editable=False) 

    def __str__(self):
        return self.title