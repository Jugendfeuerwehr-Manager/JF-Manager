# Generated by Django 3.2.6 on 2022-09-15 11:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0010_member_canswimm'),
    ]

    operations = [
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=200, verbose_name='Gruppenname')),
            ],
        ),
        migrations.AlterField(
            model_name='member',
            name='canSwimm',
            field=models.BooleanField(default=False, verbose_name='Kann schwimmen'),
        ),
        migrations.AddField(
            model_name='member',
            name='group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='members.group'),
        ),
    ]
