#!/usr/bin/env python
"""One-time fix: recreate auth_group_permissions with correct FK to auth_permission."""
import os, sys, django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jf_manager_backend.settings')

# Load .env manually
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, val = line.partition('=')
                os.environ.setdefault(key.strip(), val.strip())

django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute('SELECT id, group_id, permission_id FROM auth_group_permissions')
data = cursor.fetchall()
print(f'Saved {len(data)} existing rows')

cursor.execute('DROP TABLE IF EXISTS auth_group_permissions')
cursor.execute(
    'CREATE TABLE "auth_group_permissions" ('
    '"id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, '
    '"group_id" integer NOT NULL REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED, '
    '"permission_id" integer NOT NULL REFERENCES "auth_permission" ("id") DEFERRABLE INITIALLY DEFERRED'
    ')'
)
cursor.execute('CREATE UNIQUE INDEX agp_uniq ON auth_group_permissions (group_id, permission_id)')
cursor.execute('CREATE INDEX agp_gid ON auth_group_permissions (group_id)')
cursor.execute('CREATE INDEX agp_pid ON auth_group_permissions (permission_id)')

for row in data:
    cursor.execute('INSERT INTO auth_group_permissions VALUES (?, ?, ?)', row)

connection.connection.commit()
print('DB fix applied successfully - auth_group_permissions now references auth_permission correctly')
