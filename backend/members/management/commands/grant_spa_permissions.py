"""
Management command to grant all necessary permissions for SPA users.
Run: python manage.py grant_spa_permissions <username>
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

User = get_user_model()


class Command(BaseCommand):
    help = 'Grants necessary permissions to a user for SPA access'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to grant permissions to')
        parser.add_argument(
            '--all-users',
            action='store_true',
            help='Grant permissions to all users',
        )

    def handle(self, *args, **options):
        if options['all_users']:
            users = User.objects.all()
            self.stdout.write(self.style.SUCCESS(f'Granting permissions to all {users.count()} users...'))
        else:
            username = options['username']
            try:
                users = [User.objects.get(username=username)]
            except User.DoesNotExist:
                raise CommandError(f'User "{username}" does not exist')

        # Define models that need permissions for SPA
        models = [
            ('members', 'member'),
            ('members', 'parent'),
            ('inventory', 'item'),
            ('inventory', 'category'),
            ('inventory', 'itemvariant'),
            ('inventory', 'storagelocation'),
            ('inventory', 'stock'),
            ('inventory', 'transaction'),
            ('servicebook', 'service'),
            ('servicebook', 'attandence'),
            ('orders', 'order'),
            ('orders', 'orderitem'),
            ('orders', 'orderableitem'),
            ('orders', 'orderstatus'),
            ('qualifications', 'qualification'),
            ('qualifications', 'qualificationtype'),
            ('qualifications', 'specialtask'),
            ('qualifications', 'specialtasktype'),
        ]

        permission_types = ['view', 'add', 'change', 'delete']
        
        for user in users:
            self.stdout.write(f'Granting permissions to user: {user.username}')
            granted_count = 0
            
            for app_label, model_name in models:
                for perm_type in permission_types:
                    try:
                        permission = Permission.objects.get(
                            codename=f'{perm_type}_{model_name}',
                            content_type__app_label=app_label
                        )
                        user.user_permissions.add(permission)
                        granted_count += 1
                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(
                                f'  Permission {perm_type}_{model_name} not found for {app_label}'
                            )
                        )
            
            user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'  Successfully granted {granted_count} permissions to {user.username}'
                )
            )
        
        self.stdout.write(self.style.SUCCESS('Done!'))
