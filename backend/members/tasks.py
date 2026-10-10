import django_rq

from members.models import EmailMessage
from members.services.email_service import MemberEmailService


@django_rq.job("default")
def send_email_message_job(message_id: int) -> dict | None:
    """RQ task: send the pending recipients of one member e-mail (UX-07.2)."""
    message = EmailMessage.objects.filter(pk=message_id).first()
    if message is None:
        return None
    return MemberEmailService.send_email_message(message)
