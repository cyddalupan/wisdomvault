from django.db import migrations
from django.db import connection

def apply_character_set(apps, schema_editor):
    # MySQL specific
    if connection.vendor == 'mysql':
        schema_editor.execute("ALTER DATABASE wisdomvault CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        schema_editor.execute("ALTER TABLE chat_chat CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        schema_editor.execute("ALTER TABLE chat_chat CHANGE reply reply TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    # SQLite doesn't support ALTER DATABASE or CONVERT TO CHARACTER SET
    # So no operations are performed for SQLite

def reverse_character_set(apps, schema_editor):
    # MySQL specific reverse
    if connection.vendor == 'mysql':
        schema_editor.execute("ALTER DATABASE wisdomvault CHARACTER SET utf8 COLLATE utf8_general_ci;")
        schema_editor.execute("ALTER TABLE chat_chat CONVERT TO CHARACTER SET utf8 COLLATE utf8_general_ci;")
        schema_editor.execute("ALTER TABLE chat_chat CHANGE reply reply TEXT CHARACTER SET utf8 COLLATE utf8_general_ci;")
    # No reverse operation for SQLite as no changes were made

class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0007_userprofile_name'),
    ]

    operations = [
        migrations.RunPython(apply_character_set, reverse_character_set),
    ]
