"""Local development helper: one reliable source for keys, a startup check and a full reset.

Usage (from backend/, inside the pipenv environment):
  python dev_env.py ensure              create missing secrets in .env (never replaces a valid key)
  python dev_env.py run -- CMD ...      run CMD with .env taking precedence over inherited variables
  python dev_env.py check               verify that every stored secret decrypts with the configured key
  python dev_env.py reset --confirm ja  delete local SQLite data, uploads and cache, migrate, load demo data
  python dev_env.py totp USER           current authenticator code of a seeded demo account

Development only. Secret values are never printed.
"""

import argparse
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
ENV_FILE = BACKEND / ".env"
LOGIN_FILE = BACKEND / ".dev-demo-login"
DATABASE = BACKEND / "db.sqlite3"
UPLOADS = BACKEND / "uploads"
DEV_SETTINGS = "jf_manager_backend.settings"
DEFAULTS = {"DEBUG": "True", "REDIS_URL": "redis://localhost:6379/0", "DJANGO_SETTINGS_MODULE": DEV_SETTINGS}
KEY_HINT = (
    "Lokale Daten passen nicht zum Schlüssel in backend/.env.\n"
    "  Lokal neu beginnen (löscht lokale Daten):  VS-Code-Task „dev: Zurücksetzen und Demodaten“\n"
    "                                             oder: python dev_env.py reset --confirm ja\n"
    "  Daten behalten: ursprünglichen Schlüssel als FIELD_ENCRYPTION_PREVIOUS_KEYS in backend/.env ergänzen."
)


def read_env(path=None):
    path = path or ENV_FILE
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def valid_fernet(value):
    from cryptography.fernet import Fernet

    try:
        Fernet(value.encode("ascii"))
        return True
    except (ValueError, TypeError, UnicodeError):
        return False


def set_env_value(key, value, path=None):
    path = path or ENV_FILE
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    replaced = False
    for index, line in enumerate(lines):
        if line.split("=", 1)[0].strip() == key and not line.lstrip().startswith("#"):
            lines[index] = f"{key}={value}"
            replaced = True
    if not replaced:
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def ensure():
    from cryptography.fernet import Fernet

    values = read_env()
    changes = []
    if not values.get("DJANGO_SECRET_KEY"):
        set_env_value("DJANGO_SECRET_KEY", secrets.token_urlsafe(50))
        changes.append("DJANGO_SECRET_KEY erzeugt")
    key = values.get("FIELD_ENCRYPTION_KEY", "")
    if not valid_fernet(key):
        # A missing or malformed key cannot have encrypted anything readable; a valid one is never replaced.
        set_env_value("FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode())
        changes.append("FIELD_ENCRYPTION_KEY " + ("ersetzt (ungültig)" if key else "erzeugt"))
    for name, default in DEFAULTS.items():
        if name == "DJANGO_SETTINGS_MODULE":
            continue
        if not values.get(name):
            set_env_value(name, default)
            changes.append(f"{name}={default} gesetzt")
    print("backend/.env: " + ("; ".join(changes) if changes else "vollständig"))


def environment():
    env = dict(os.environ)
    env.update({key: value for key, value in DEFAULTS.items() if key not in ("REDIS_URL",)})
    # .env wins over inherited variables, e.g. a stale key exported in the shell that started VS Code.
    env.update(read_env())
    env["PIPENV_DONT_LOAD_ENV"] = "1"
    env.setdefault("PYTHONUNBUFFERED", "1")
    return env


def manage(*args, check=True, **kwargs):
    return subprocess.run([sys.executable, "manage.py", *args], cwd=BACKEND, env=environment(), check=check, **kwargs)


def check():
    result = manage("rotate_field_encryption", check=False, capture_output=True, text=True)
    if result.returncode == 0:
        print("Schlüsselprüfung: " + (result.stdout.strip().splitlines() or ["ok"])[-1])
        return 0
    print("Schlüsselprüfung fehlgeschlagen.\n" + KEY_HINT, file=sys.stderr)
    return 3


def flush_cache(env):
    url = env.get("REDIS_URL", "none")
    if url in ("", "none"):
        return
    try:
        import redis

        client = redis.Redis.from_url(url)
        # Only cache entries of this application; RQ queues and other data stay untouched.
        keys = list(client.scan_iter("jf_manager_backend:*", count=500))
        if keys:
            client.delete(*keys)
        print(f"Cache: {len(keys)} Einträge entfernt")
    except Exception as exc:  # Redis is optional in development
        print(f"Cache nicht geleert ({type(exc).__name__}); Redis läuft vermutlich nicht.")


def reset(confirm):
    if confirm != "ja":
        print("Abgebrochen: lokale Daten bleiben erhalten (Bestätigung mit --confirm ja).")
        return 1
    env = environment()
    if env.get("DJANGO_SETTINGS_MODULE") != DEV_SETTINGS:
        print(f"Abgebrochen: Reset nur mit {DEV_SETTINGS} (lokale SQLite-Datenbank).", file=sys.stderr)
        return 2
    ensure()
    for path in (DATABASE, DATABASE.with_name("db.sqlite3-journal"), DATABASE.with_name("db.sqlite3-wal")):
        path.unlink(missing_ok=True)
    if UPLOADS.exists():
        shutil.rmtree(UPLOADS)
    UPLOADS.mkdir()
    flush_cache(environment())
    manage("migrate", "--verbosity", "0")
    password = secrets.token_urlsafe(12)
    manage("seed_demo", "--password", password)
    LOGIN_FILE.write_text(
        "Benutzer: admin (und weitere, siehe oben)\n"
        "Portal: eltern@demo.example.invalid, mitglied@demo.example.invalid\n"
        f"Passwort: {password}\n",
        encoding="utf-8",
    )
    os.chmod(LOGIN_FILE, 0o600)
    print(f"Zugang gespeichert in backend/{LOGIN_FILE.name} (nur lokal, nicht versioniert).")
    return check()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("ensure")
    commands.add_parser("check")
    run_parser = commands.add_parser("run")
    run_parser.add_argument("cmd", nargs=argparse.REMAINDER)
    reset_parser = commands.add_parser("reset")
    reset_parser.add_argument("--confirm", default="")
    totp_parser = commands.add_parser("totp")
    totp_parser.add_argument("username")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(line_buffering=True)  # keep order with subprocess output
    if args.command == "ensure":
        ensure()
        return 0
    if args.command == "check":
        return check()
    if args.command == "reset":
        return reset(args.confirm)
    if args.command == "totp":
        return manage("demo_totp", args.username, check=False).returncode
    cmd = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd
    if not cmd:
        parser.error("run benötigt einen Befehl")
    if cmd[0] == "python":
        cmd[0] = sys.executable
    os.chdir(BACKEND)
    os.execvpe(cmd[0], cmd, environment())
    return 0  # pragma: no cover


if __name__ == "__main__":
    sys.exit(main())
