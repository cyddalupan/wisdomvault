# Generated by Django 5.1.2 on 2024-12-29 06:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0003_remove_userprofile_email_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="task",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
