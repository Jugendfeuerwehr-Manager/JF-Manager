import django_rq


@django_rq.job("default")
def send_password_reset_job(email: str) -> None:
    """RQ task: look up the account and send the reset mail outside the request."""
    from users.api_views import send_password_reset

    send_password_reset(email)
