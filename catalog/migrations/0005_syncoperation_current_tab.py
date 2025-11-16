# Generated migration for multi-tab parsing feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0004_syncoperation'),
    ]

    operations = [
        migrations.AddField(
            model_name='syncoperation',
            name='current_tab',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Name of the currently processing Google Sheets tab',
                max_length=100
            ),
        ),
    ]
