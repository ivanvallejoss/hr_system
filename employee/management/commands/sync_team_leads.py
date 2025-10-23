from django.core.management.base import BaseCommand;
from employee.models import Employee;
from django.contrib.auth.models import Group;

class Command(BaseCommand):
    help = 'Sincroniza team leads con el grupo Team_lead'

    def handle(self, *args, **kwargs):
        team_lead_group, created = Group.objects.get_or_create(name='Team_Lead')

        if created:
            self.stdout.write(self.style.SUCCESS('Group Team_Lead creado!'))

        synced = 0
        for employee in Employee.objects.all():
            employee.sync_team_lead_group()
            if employee.is_team_lead:
                synced += 1

        self.stdout.write(self.style.SUCCESS(f'{synced} team leads sincronizados!'))