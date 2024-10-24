# Generated by Django 5.0.3 on 2024-10-22 20:23

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0034_comparisonfeedback_shown_first'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='comparisonfeedback',
            name='player',
        ),
        migrations.AddField(
            model_name='comparisonfeedback',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='game.user'),
        ),
    ]
