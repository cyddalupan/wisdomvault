# Generated by Django 5.1.2 on 2024-12-30 06:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0004_alter_userprofile_task"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="user_type",
            field=models.CharField(default="", max_length=255),
            preserve_default=False,
        ),
    ]
