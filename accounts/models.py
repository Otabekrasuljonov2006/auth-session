from django.db import models
from django.contrib.auth.models import User


class Event(models.Model):
    name = models.CharField(max_length=120)
    venue = models.CharField(max_length=120)
    starts_at = models.DateTimeField()

    def __str__(self):
        return f"{self.name} @ {self.venue}"


class Ticket(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_USED = "used"
    STATUS_BLOCKED = "blocked"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_USED, "Used"),
        (STATUS_BLOCKED, "Blocked"),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="tickets")
    holder_name = models.CharField(max_length=120)
    holder_doc_id = models.CharField(max_length=64)
    seat_code = models.CharField(max_length=20)
    qr_payload = models.TextField(unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.holder_name} - {self.event.name} - {self.seat_code}"


class ScanDecisionLog(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="scan_logs")
    scanner = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    approved = models.BooleanField(default=False)
    confidence = models.FloatField(default=0.0)
    reasons = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ticket_id} - {'OK' if self.approved else 'DENY'}"
