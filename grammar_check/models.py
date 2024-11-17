from django.db import models
import mistune
from django.utils.safestring import mark_safe

class GrammarCheck(models.Model):
    user_input = models.TextField()
    corrected_output = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def formatted_output(self):
        markdown = mistune.create_markdown(renderer=mistune.HTMLRenderer())
        html = markdown(self.corrected_output)
        return mark_safe(html)
    
    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"GrammarCheck {self.id}"