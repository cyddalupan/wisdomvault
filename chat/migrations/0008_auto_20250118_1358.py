from django.db import migrations, connection
from django.db import transaction

def apply_character_set(apps, schema_editor):
    # Check if the database is MySQL
    if connection.vendor == 'mysql':
        # Only run DDL outside of a transaction for MySQL
        with connection.cursor() as cursor:
            cursor.execute("ALTER DATABASE wisdomvault CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            cursor.execute("ALTER TABLE chat_chat CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            cursor.execute("ALTER TABLE chat_chat CHANGE reply reply TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    # SQLite doesn't support ALTER DATABASE or CONVERT TO CHARACTER SET, so do nothing here.

def reverse_character_set(apps, schema_editor):
    # Check if the database is MySQL
    if connection.vendor == 'mysql':
        # Only run DDL outside of a transaction for MySQL
        with connection.cursor() as cursor:
            cursor.execute("ALTER DATABASE wisdomvault CHARACTER SET utf8 COLLATE utf8_general_ci;")
            cursor.execute("ALTER TABLE chat_chat CONVERT TO CHARACTER SET utf8 COLLATE utf8_general_ci;")
            cursor.execute("ALTER TABLE chat_chat CHANGE reply reply TEXT CHARACTER SET utf8 COLLATE utf8_general_ci;")
    # SQLite doesn't support reverse DDL operations, so do nothing here.

class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0007_userprofile_name'),
    ]

    operations = [
        # Run DDL operations outside of a transaction for MySQL and SQLite
        migrations.RunPython(apply_character_set, reverse_character_set),
    ]
