import contextlib
import os
import tempfile

_cached_ca_cert_content: str | None = None
_cached_ca_cert_path: str | None = None


def _write_ca_cert_tempfile(ca_cert_content: str) -> str:
    global _cached_ca_cert_content, _cached_ca_cert_path

    normalized = ca_cert_content.strip()
    if _cached_ca_cert_content == normalized and _cached_ca_cert_path and os.path.exists(_cached_ca_cert_path):
        return _cached_ca_cert_path

    if _cached_ca_cert_path and os.path.exists(_cached_ca_cert_path):
        with contextlib.suppress(OSError):
            os.unlink(_cached_ca_cert_path)

    fd, path = tempfile.mkstemp(prefix="jf_manager_ldap_ca_", suffix=".pem")
    with os.fdopen(fd, "w", encoding="utf-8") as cert_file:
        cert_file.write(normalized)
        cert_file.write("\n")

    _cached_ca_cert_content = normalized
    _cached_ca_cert_path = path
    return path


def apply_ldap_tls_options(config) -> None:
    """Apply TLS certificate validation options for python-ldap globally."""
    import ldap

    cert_validation_disabled = bool(getattr(config, "disable_cert_validation", False))
    ca_cert_file = (getattr(config, "ca_cert_file", "") or "").strip()
    ca_cert_content = (getattr(config, "ca_cert_content", "") or "").strip()

    if cert_validation_disabled:
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, "")
    else:
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_DEMAND)

        resolved_ca_path = ""
        if ca_cert_content:
            resolved_ca_path = _write_ca_cert_tempfile(ca_cert_content)
        elif ca_cert_file:
            if not os.path.isfile(ca_cert_file):
                raise ValueError("Configured LDAP CA certificate file does not exist.")
            resolved_ca_path = ca_cert_file

        ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, resolved_ca_path)

    if hasattr(ldap, "OPT_X_TLS_NEWCTX"):
        ldap.set_option(ldap.OPT_X_TLS_NEWCTX, 0)
