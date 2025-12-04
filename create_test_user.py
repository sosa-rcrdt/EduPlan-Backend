import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eduplan_api.settings')
django.setup()

from django.contrib.auth.models import User

username = 'testuser'
password = 'testpassword123'
email = 'test@example.com'

if not User.objects.filter(username=username).exists():
    User.objects.create_user(username=username, password=password, email=email)
    print(f"User '{username}' created.")
else:
    print(f"User '{username}' already exists.")
