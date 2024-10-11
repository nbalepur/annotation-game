# Generated by Django 5.0.3 on 2024-09-30 21:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0020_toollog'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='toollog',
            name='question',
        ),
        migrations.RemoveField(
            model_name='toollog',
            name='user',
        ),
        migrations.AddField(
            model_name='toollog',
            name='question_id',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='toollog',
            name='user_id',
            field=models.IntegerField(default=0),
        ),
    ]