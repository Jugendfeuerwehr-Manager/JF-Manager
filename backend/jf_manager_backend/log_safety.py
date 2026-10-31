"""Keep personal data out of application logs (DSGVO data minimisation)."""


def mask_email(address):
    """``eva.muster@example.org`` -> ``e***@example.org``; enough to tell recipients apart."""
    if not address or "@" not in str(address):
        return "***"
    local, _, domain = str(address).partition("@")
    return f"{local[:1]}***@{domain}"
