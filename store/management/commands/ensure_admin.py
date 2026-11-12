import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Idempotently creates the initial staff superuser from environment variables if no matching user exists."

    def handle(self, *args, **options):
        username = (os.getenv("DJANGO_ADMIN_USERNAME") or "").strip()
        password = os.getenv("DJANGO_ADMIN_PASSWORD") or ""
        email = (os.getenv("DJANGO_ADMIN_EMAIL") or "").strip()

        if not username or not password:
            self.stdout.write("ensure_admin: DJANGO_ADMIN_USERNAME/DJANGO_ADMIN_PASSWORD not set; skipping.")
            return

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"ensure_admin: user '{username}' already exists; skipping.")
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"ensure_admin: superuser '{username}' created cleanly."))

