import markdown
from django.utils.safestring import mark_safe
from django.db import models

class QuestionAnswer(models.Model):
    title = models.CharField(max_length=255)
    question = models.TextField()
    answer = models.TextField(editable=False) 

    def formatted_answer(self):
        """Converts the markdown text to HTML and returns it as a safe string."""
        html = markdown.markdown(self.answer, extensions=['fenced_code', 'codehilite'])
        return mark_safe(html)

    def __str__(self):
        return self.title