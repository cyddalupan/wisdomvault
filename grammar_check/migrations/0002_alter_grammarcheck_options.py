# Generated by Django 5.1.2 on 2024-11-27 04:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("grammar_check", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="grammarcheck",
            options={"ordering": ["-id"]},
        ),
    ]