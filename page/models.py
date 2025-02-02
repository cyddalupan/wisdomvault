from django.db import models

class FacebookPage(models.Model):
    page_id = models.CharField(max_length=50, unique=True) 
    token = models.CharField(max_length=255)
    page_name = models.CharField(max_length=255)
    sheet_id = models.CharField(max_length=255)
    info = models.TextField(blank=True, null=True)
    additional_info = models.TextField(blank=True, null=True)
    sales = models.TextField(blank=True, null=True)

    # Feature toggles
    is_inventory = models.BooleanField(default=True)
    is_pos = models.BooleanField(default=True)
    is_leads = models.BooleanField(default=True)
    is_scheduling = models.BooleanField(default=True)
    is_online_selling = models.BooleanField(default=True)

    def __str__(self):
        return self.page_name

    class Meta:
        verbose_name = "Facebook Page"
        verbose_name_plural = "Facebook Pages"