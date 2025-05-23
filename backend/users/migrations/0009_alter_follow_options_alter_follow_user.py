# Generated by Django 4.2.20 on 2025-04-08 18:30

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_alter_follow_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='follow',
            options={'default_related_name': ('followers',), 'ordering': ('user',), 'verbose_name': 'Подписка', 'verbose_name_plural': 'Подписки'},
        ),
        migrations.AlterField(
            model_name='follow',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscribers', to=settings.AUTH_USER_MODEL, verbose_name='Подписчик'),
        ),
    ]
