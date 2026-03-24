import json
from io import BytesIO

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core import signing
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import Event, ScanDecisionLog, Ticket


@csrf_exempt
def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        if not username or not password:
            return HttpResponse("Qaysidir maydon bo'sh")
        if User.objects.filter(username=username).exists():
            return HttpResponse("Bu nomdagi foydalanuvchi avvaldan bor")
        User.objects.create_user(username=username, password=password)
        return redirect("login")
    return render(request, "accounts/register.html")


@csrf_exempt
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("profile")
        return HttpResponse("Bunday foydalanuvchi mavjud emas")
    return render(request, "accounts/login.html")


@csrf_exempt
@login_required
def profile_view(request):
    return render(request, "accounts/profile.html")


@csrf_exempt
def logout_view(request):
    logout(request)
    return redirect("login")


def _build_ticket_payload(ticket: Ticket) -> str:
    payload = {
        "ticket_id": ticket.id,
        "event_id": ticket.event_id,
        "seat": ticket.seat_code,
        "holder_doc_id": ticket.holder_doc_id,
    }
    return signing.dumps(payload, salt="ticket-qr-v1")


def _simple_pdf(ticket: Ticket) -> bytes:
    lines = [
        "%PDF-1.1",
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj",
    ]
    text = (
        "BT /F1 12 Tf 50 760 Td "
        f"(Event: {ticket.event.name}) Tj T* "
        f"(Venue: {ticket.event.venue}) Tj T* "
        f"(Seat: {ticket.seat_code}) Tj T* "
        f"(Holder: {ticket.holder_name}) Tj T* "
        "(QR payload to encode in ticket QR:) Tj T* "
        f"({ticket.qr_payload[:90]}) Tj ET"
    )
    lines.append(f"4 0 obj << /Length {len(text)} >> stream\n{text}\nendstream endobj")
    lines.append("5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj")

    xref_offset = sum(len(f"{line}\n".encode("latin1", "ignore")) for line in lines)
    pdf = BytesIO()
    for line in lines:
        pdf.write(f"{line}\n".encode("latin1", "ignore"))
    pdf.write(b"xref\n0 6\n0000000000 65535 f \n")

    offset = 0
    for line in lines:
        pdf.write(f"{offset:010} 00000 n \n".encode())
        offset += len(f"{line}\n".encode("latin1", "ignore"))

    pdf.write(
        f"trailer << /Root 1 0 R /Size 6 >>\nstartxref\n{xref_offset}\n%%EOF".encode()
    )
    return pdf.getvalue()


def _ai_decision(ticket: Ticket, seat: str, holder_doc_id: str):
    score = 1.0
    reasons = []

    if ticket.status == Ticket.STATUS_USED:
        score -= 0.7
        reasons.append("Chipta avval ishlatilgan")

    if ticket.status == Ticket.STATUS_BLOCKED:
        score -= 0.9
        reasons.append("Chipta bloklangan")

    if ticket.seat_code != seat:
        score -= 0.5
        reasons.append("Skanerlangan joy chiptadagi joyga mos emas")

    if ticket.holder_doc_id != holder_doc_id:
        score -= 0.4
        reasons.append("Hujjat raqami chiptadagi ma'lumotga mos emas")

    approved = score >= 0.6
    if approved and not reasons:
        reasons.append("Barcha tekshiruvlardan muvaffaqiyatli o'tdi")

    return approved, max(0.0, round(score, 2)), reasons


@csrf_exempt
@login_required
def create_ticket_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST so'rovi yuboring"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON noto'g'ri"}, status=400)

    required_fields = ["event_name", "venue", "starts_at", "holder_name", "holder_doc_id", "seat_code"]
    missing = [field for field in required_fields if not payload.get(field)]
    if missing:
        return JsonResponse({"error": f"Majburiy maydonlar yo'q: {', '.join(missing)}"}, status=400)

    event, _ = Event.objects.get_or_create(
        name=payload["event_name"],
        venue=payload["venue"],
        starts_at=payload["starts_at"],
    )

    ticket = Ticket.objects.create(
        event=event,
        holder_name=payload["holder_name"],
        holder_doc_id=payload["holder_doc_id"],
        seat_code=payload["seat_code"],
        qr_payload="pending",
    )
    ticket.qr_payload = _build_ticket_payload(ticket)
    ticket.save(update_fields=["qr_payload"])

    pdf_bytes = _simple_pdf(ticket)

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="ticket-{ticket.id}.pdf"'
    response["X-Ticket-QR-Payload"] = ticket.qr_payload
    return response


@csrf_exempt
@login_required
def scan_ticket_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST so'rovi yuboring"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON noto'g'ri"}, status=400)

    qr_payload = payload.get("qr_payload")
    seat = payload.get("seat_code")
    holder_doc_id = payload.get("holder_doc_id")
    if not qr_payload or not seat or not holder_doc_id:
        return JsonResponse({"error": "qr_payload, seat_code, holder_doc_id kerak"}, status=400)

    try:
        data = signing.loads(qr_payload, salt="ticket-qr-v1", max_age=60 * 60 * 24)
    except signing.BadSignature:
        return JsonResponse({"approved": False, "confidence": 0.0, "reasons": ["QR imzosi noto'g'ri"]}, status=400)
    except signing.SignatureExpired:
        return JsonResponse({"approved": False, "confidence": 0.0, "reasons": ["QR eskirgan"]}, status=400)

    ticket = Ticket.objects.filter(id=data.get("ticket_id"), qr_payload=qr_payload).select_related("event").first()
    if not ticket:
        return JsonResponse({"approved": False, "confidence": 0.0, "reasons": ["Chipta topilmadi"]}, status=404)

    approved, confidence, reasons = _ai_decision(ticket, seat, holder_doc_id)
    if approved:
        ticket.status = Ticket.STATUS_USED
        ticket.checked_in_at = timezone.now()
        ticket.save(update_fields=["status", "checked_in_at"])

    ScanDecisionLog.objects.create(
        ticket=ticket,
        scanner=request.user,
        approved=approved,
        confidence=confidence,
        reasons="; ".join(reasons),
    )

    return JsonResponse(
        {
            "approved": approved,
            "confidence": confidence,
            "ticket": {
                "id": ticket.id,
                "event": ticket.event.name,
                "seat": ticket.seat_code,
                "holder_name": ticket.holder_name,
            },
            "reasons": reasons,
        }
    )
