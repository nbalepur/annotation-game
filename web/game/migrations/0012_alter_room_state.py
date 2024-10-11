# Generated by Django 4.0.6 on 2024-09-13 15:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0011_alter_question_is_human_written'),
    ]

    operations = [
        migrations.AlterField(
            model_name='room',
            name='state',
            field=models.CharField(choices=[('idle', 'Idle'), ('playing', 'Playing'), ('contest', 'Contest'), ('instruct', 'Instruction')], default='idle', max_length=9),
        ),
    ]