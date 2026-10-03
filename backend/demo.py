"""Create fictitious demo data in a NEW temporary database and serve locally.

Usage: pipenv run python demo.py [--port 8011]
Never reads or writes the normal application database. No real emails or push.
"""
import argparse
import os
import secrets
import tempfile
from datetime import date, datetime, time, timedelta
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8011)
    args = parser.parse_args()
    directory = Path(tempfile.mkdtemp(prefix="jf-manager-demo-"))
    os.environ.update({"DJANGO_SETTINGS_MODULE": "jf_manager_backend.demo_settings", "DEBUG": "True",
                       "DJANGO_SECRET_KEY": secrets.token_urlsafe(48), "JF_DEMO_DATABASE": str(directory / "demo.sqlite3"),
                       "REDIS_URL": "none"})
    import django
    django.setup()
    from django.contrib.auth import get_user_model
    from django.core.management import call_command
    from django.utils import timezone

    from departments.models import Department, UserDepartmentRole
    from members.models import Group, Member, Parent, Status
    from servicebook.models import Attendance, Service, StaffAttendance
    from training.models import TrainingSession

    call_command("migrate", verbosity=0)
    department = Department.objects.create(name="Jugendfeuerwehr Musterstadt", code="musterstadt", color="#b91c1c")
    password = secrets.token_urlsafe(16)
    leader = get_user_model().objects.create_superuser(username="demo", email="demo@example.invalid", password=password,
                                                       first_name="Alex", last_name="Sommer", favorite_department=department)
    staff = [leader]
    for username, first, last in (("mira", "Mira", "Brandt"), ("jan", "Jan", "Keller"), ("sam", "Sam", "Winter")):
        user = get_user_model().objects.create_user(username=username, first_name=first, last_name=last)
        user.set_unusable_password()
        user.save()
        staff.append(user)
    for person in staff:
        UserDepartmentRole.objects.create(user=person, department=department)
    group = Group.objects.create(name="Löschfüchse", department=department)
    status = Status.objects.create(name="Aktiv", color="#16a34a")
    people = []
    names = [("Lena", "Berg"), ("Finn", "Weber"), ("Mila", "Hoffmann"), ("Noah", "Fischer"),
             ("Emilia", "Koch"), ("Ben", "Schneider"), ("Luca", "Hartmann"), ("Lea", "Wagner"),
             ("Jonas", "Becker"), ("Anna", "Klein"), ("Elias", "Wolf"), ("Nele", "Braun")]
    for index, (first, last) in enumerate(names):
        person = Member.objects.create(name=first, lastname=last, birthday=date(2012 + index % 3, index % 12 + 1, 12),
                                       joined=date(2024, 3, 1), group=group, status=status, city="Musterstadt", canSwimm=True)
        person.departments.add(department)
        people.append(person)
        parent = Parent.objects.create(name="Kim", lastname=last, email=f"familie{index+1}@example.invalid", city="Musterstadt")
        parent.children.add(person)
    today = timezone.localdate()
    topics = ["Löschangriff: Gemeinsam zum Ziel", "Erste Hilfe im Team", "Fahrzeugkunde & Geräte", "Knoten und Stiche"]
    for index, topic in enumerate(topics):
        start = timezone.make_aware(datetime.combine(today-timedelta(days=7*index+1), time(17, 30)))
        service = Service.objects.create(start=start, end=start+timedelta(hours=2), place="Feuerwehrhaus Musterstadt", topic=topic,
                                         description="Gemeinsam üben, Aufgaben verteilen und zum Abschluss Erfahrungen austauschen.", department=department)
        service.operations_manager.add(leader)
        for i, person in enumerate(people):
            if i < 9 or index > 0:
                Attendance.objects.create(person=person, service=service, state="E" if i == 3 else "F" if i == 7 else "A")
        for i, person in enumerate(staff):
            if i < 3:
                StaffAttendance.objects.create(person=person, service=service, state="E" if i == 2 else "A")
    training = TrainingSession.objects.create(title="Wasser marsch – Stationsausbildung", date=today+timedelta(days=5),
                                             start_time=time(17,30), end_time=time(19,30), location="Übungshof", department=department, created_by=leader)
    training.groups.add(group)
    # Credentials stay in the temporary demo directory for repeatable local UI checks.
    import json
    (directory / "login.json").write_text(json.dumps({"username": "demo", "password": password}))
    os.chmod(directory / "login.json", 0o600)
    print(f"\nDemo-Datenbank: {directory}\nBenutzer: demo\nPasswort: {password}\nAPI: http://127.0.0.1:{args.port}/api/v1\n", flush=True)
    call_command("runserver", f"127.0.0.1:{args.port}", use_reloader=False)


if __name__ == "__main__":
    main()
