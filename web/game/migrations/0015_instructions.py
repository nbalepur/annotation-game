# Generated by Django 4.0.6 on 2024-09-13 16:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0014_room_uses_instructions'),
    ]

    operations = [
        migrations.CreateModel(
            name='Instructions',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('instruction_steps', models.JSONField(blank=True, null=True)),
            ],
        ),
    ]