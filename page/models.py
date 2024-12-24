from django.db import models

class FacebookPage(models.Model):
    page_id = models.CharField(max_length=50, unique=True) 
    token = models.CharField(max_length=255)
    agency_name = models.CharField(max_length=255)
    establishment_date = models.CharField(max_length=255)
    deployment_countries = models.CharField(max_length=255)
    agency_location = models.CharField(max_length=255)
    cash_assistance_statement = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.agency_name

    class Meta:
        verbose_name = "Facebook Page"
        verbose_name_plural = "Facebook Pages"