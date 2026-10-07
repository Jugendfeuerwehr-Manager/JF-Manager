"""Create fictitious demo data in a NEW temporary database and serve locally.

Usage: pipenv run python demo.py [--port 8011]
Never reads or writes the normal application database. No real emails or push.
"""

import argparse
import os
import secrets
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8011)
    args = parser.parse_args()
    directory = Path(tempfile.mkdtemp(prefix="jf-manager-demo-"))
    from cryptography.fernet import Fernet

    # Throwaway secrets: the demo never shares keys with the real database.
    os.environ.update(
        {
            "DJANGO_SETTINGS_MODULE": "jf_manager_backend.demo_settings",
            "DEBUG": "True",
            "DJANGO_SECRET_KEY": secrets.token_urlsafe(48),
            "JF_DEMO_DATABASE": str(directory / "demo.sqlite3"),
            "FIELD_ENCRYPTION_KEY": Fernet.generate_key().decode(),
            "REDIS_URL": "none",
        }
    )
    import django

    django.setup()
    import json

    from django.core.management import call_command

    call_command("migrate", verbosity=0)
    password = secrets.token_urlsafe(16)
    call_command("seed_demo", password=password)
    # Credentials and the run's environment stay in the temporary demo directory (0600).
    (directory / "login.json").write_text(json.dumps({"username": "admin", "password": password}))
    keys = (
        "DJANGO_SETTINGS_MODULE",
        "DEBUG",
        "DJANGO_SECRET_KEY",
        "JF_DEMO_DATABASE",
        "FIELD_ENCRYPTION_KEY",
        "REDIS_URL",
    )
    (directory / "demo.env").write_text("".join(f"{key}={os.environ[key]}\n" for key in keys))
    for name in ("login.json", "demo.env"):
        os.chmod(directory / name, 0o600)
    print(
        f"\nDemo-Datenbank: {directory}\nAPI: http://127.0.0.1:{args.port}/api/v1\n"
        f"Anmeldecode: env $(cat {directory}/demo.env | xargs) pipenv run python manage.py demo_totp admin\n",
        flush=True,
    )
    call_command("runserver", f"127.0.0.1:{args.port}", use_reloader=False)


if __name__ == "__main__":
    main()
