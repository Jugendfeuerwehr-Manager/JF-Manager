# Generated by Django 2.1.5 on 2019-10-31 15:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0008_auto_20191031_1501'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='datetime',
            field=models.DateField(verbose_name='Datum'),
        ),
    ]