# Generated by Django 4.0.6 on 2024-09-13 20:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0017_room_player_map'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='channel_name',
            field=models.CharField(blank=True, default='', max_length=320),
        ),
    ]
