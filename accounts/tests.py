import json

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Ticket


class TicketFlowTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="scanner", password="secret123")
        self.client = Client()
        self.client.login(username="scanner", password="secret123")

    def test_create_and_scan_ticket_success(self):
        create_payload = {
            "event_name": "AI Concert",
            "venue": "Humo Arena",
            "starts_at": timezone.now().isoformat(),
            "holder_name": "Ali Valiyev",
            "holder_doc_id": "AA1234567",
            "seat_code": "A-10",
        }
        create_resp = self.client.post(
            reverse("create_ticket_api"),
            data=json.dumps(create_payload),
            content_type="application/json",
        )

        self.assertEqual(create_resp.status_code, 200)
        qr_payload = create_resp["X-Ticket-QR-Payload"]
        self.assertTrue(qr_payload)

        scan_resp = self.client.post(
            reverse("scan_ticket_api"),
            data=json.dumps(
                {
                    "qr_payload": qr_payload,
                    "seat_code": "A-10",
                    "holder_doc_id": "AA1234567",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(scan_resp.status_code, 200)
        data = scan_resp.json()
        self.assertTrue(data["approved"])

        ticket = Ticket.objects.get(id=data["ticket"]["id"])
        self.assertEqual(ticket.status, Ticket.STATUS_USED)

    def test_scan_with_wrong_seat_is_rejected(self):
        create_payload = {
            "event_name": "AI Concert",
            "venue": "Humo Arena",
            "starts_at": timezone.now().isoformat(),
            "holder_name": "Ali Valiyev",
            "holder_doc_id": "AA1234567",
            "seat_code": "A-10",
        }
        create_resp = self.client.post(
            reverse("create_ticket_api"),
            data=json.dumps(create_payload),
            content_type="application/json",
        )
        qr_payload = create_resp["X-Ticket-QR-Payload"]

        scan_resp = self.client.post(
            reverse("scan_ticket_api"),
            data=json.dumps(
                {
                    "qr_payload": qr_payload,
                    "seat_code": "B-99",
                    "holder_doc_id": "AA1234567",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(scan_resp.status_code, 200)
        data = scan_resp.json()
        self.assertFalse(data["approved"])
