# Generated by Django 5.1.3 on 2024-11-30 06:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kanbanapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='board',
            name='closed',
            field=models.BooleanField(default=False),
        ),
    ]