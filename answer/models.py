from django.conf import settings  # Import settings to refer to the user model
from django.db import models
import markdown2
from django.utils.safestring import mark_safe

class QuestionAnswer(models.Model):
    title = models.CharField(max_length=255)
    question = models.TextField()
    answer = models.TextField(editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    def formatted_answer(self):
        """Converts the markdown text to HTML and returns it as a safe string."""
        html = markdown2.markdown(self.answer, extras=['fenced_code', 'codehilite'])
        return mark_safe(html)

    def __str__(self):
        return self.title