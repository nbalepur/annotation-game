# Generated by Django 4.0.6 on 2024-09-13 20:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0016_delete_instructions_question_instructions_a_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='room',
            name='player_map',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
