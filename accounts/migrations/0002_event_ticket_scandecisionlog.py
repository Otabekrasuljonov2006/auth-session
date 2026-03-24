from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Event",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("venue", models.CharField(max_length=120)),
                ("starts_at", models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name="Ticket",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("holder_name", models.CharField(max_length=120)),
                ("holder_doc_id", models.CharField(max_length=64)),
                ("seat_code", models.CharField(max_length=20)),
                ("qr_payload", models.TextField(unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("used", "Used"), ("blocked", "Blocked")],
                        default="active",
                        max_length=10,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("checked_in_at", models.DateTimeField(blank=True, null=True)),
                (
                    "event",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tickets", to="accounts.event"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ScanDecisionLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("approved", models.BooleanField(default=False)),
                ("confidence", models.FloatField(default=0.0)),
                ("reasons", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "scanner",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
                ),
                (
                    "ticket",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scan_logs", to="accounts.ticket"),
                ),
            ],
        ),
    ]
