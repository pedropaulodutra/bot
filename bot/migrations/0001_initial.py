# Generated by Django 5.2.4 on 2025-07-23 19:19

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BotControl',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_running', models.BooleanField(default=False)),
                ('symbol', models.CharField(default='BTCUSDT', max_length=20)),
                ('timeframe', models.CharField(default='15m', max_length=10)),
                ('ema_fast', models.IntegerField(default=6)),
                ('ema_slow', models.IntegerField(default=12)),
                ('quantidade_usdt', models.FloatField(default=20.0)),
                ('leverage', models.IntegerField(default=5)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('api_key', models.CharField(blank=True, max_length=200, null=True)),
                ('api_secret', models.CharField(blank=True, max_length=200, null=True)),
                ('telegram_bot_token', models.CharField(blank=True, max_length=100, null=True)),
                ('telegram_chat_id', models.CharField(blank=True, max_length=50, null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
