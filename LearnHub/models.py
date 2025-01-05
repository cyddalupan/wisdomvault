from django.db import models
import mistune
from django.utils.safestring import mark_safe

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