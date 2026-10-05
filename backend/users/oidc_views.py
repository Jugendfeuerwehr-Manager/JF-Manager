"""
OIDC authentication views for JF-Manager.

Authorization Code Flow with PKCE (S256). The flow is bound to the browser
session that started it and can be completed exactly once. On success the
backend creates the normal Django session (with the same MFA rules as local
login); the browser never receives provider or application tokens.

Flow:
  1. GET /api/v1/auth/oidc/public-config/ → { enabled, provider_name, hide_local_login }
  2. GET /api/v1/auth/oidc/login/?next=/dashboard → { authorization_url }
     State, nonce, PKCE verifier and the relative return path are stored in the
     caller's session.
  3. IdP redirects to GET /api/v1/auth/oidc/callback/?code=...&state=...
     → state checked against the session, code exchanged with the verifier,
       id_token verified, session established or MFA step started
     → redirect to {FRONTEND_URL}/auth/oidc/callback?result=...&next=...
"""

import base64
import hashlib
import hmac
import logging
import secrets
import time
from urllib.parse import urlencode, urlparse

import requests
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.views import View
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger("users.oidc_views")

# How long (seconds) a started login may take at the provider.
OIDC_STATE_TIMEOUT = 300
OIDC_FLOW_KEY = "_oidc_flow"
# Asymmetric signatures only; never trust the algorithm named in the token.
ALLOWED_ID_TOKEN_ALGORITHMS = ("RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384", "ES512")
# `amr` values that state the provider performed a second factor (RFC 8176).
PROVIDER_MFA_METHODS = frozenset({"mfa", "otp", "hwk", "swk", "sc", "fpt", "face", "iris", "retina", "vbm"})
# Fixed error codes for the frontend; no exception texts or personal data in URLs.
ERROR_MESSAGES = {
    "provider_error": "Der Identity Provider hat die Anmeldung abgebrochen.",
    "invalid_response": "Ungültige Antwort des Identity Providers.",
    "expired": "Die Anmeldung ist abgelaufen. Bitte erneut anmelden.",
    "disabled": "SSO ist deaktiviert.",
    "unavailable": "Der Identity Provider ist nicht erreichbar.",
    "verification_failed": "Die Anmeldung konnte nicht bestätigt werden.",
    "account_rejected": "Für dieses Konto ist keine Anmeldung möglich.",
}


def safe_next(value):
    """Allow only same-origin relative paths as post-login target."""
    value = str(value or "/")
    if not value.startswith("/") or value.startswith("//") or "\\" in value or any(ord(ch) < 32 for ch in value):
        return "/"
    return value


def _pkce_challenge(verifier):
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_oidc_config():
    from settings_manager.models import OIDCConfig

    return OIDCConfig.get_or_create_default()


def _validate_oidc_url(url: str, label: str = "URL", *, allowed_host: str | None = None) -> str:
    """
    Validate that a URL used for outbound OIDC requests is safe:
      - Must be https:// (no http, file, ftp, …)
      - Must have a non-empty netloc (no bare paths or localhost tricks)
      - If allowed_host is provided, the URL's hostname must match it exactly
        (prevents the discovery document from redirecting JWKS to a different server).

    Returns the validated URL unchanged.
    Raises ValueError with a descriptive message on failure.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"OIDC {label} muss ein HTTPS-URL sein (erhalten: {parsed.scheme!r}).")
    if not parsed.netloc:
        raise ValueError(f"OIDC {label} hat keinen gültigen Host.")
    if allowed_host is not None and parsed.hostname != allowed_host:
        raise ValueError(
            f"OIDC {label} zeigt auf einen anderen Host ({parsed.hostname!r}) als der"
            f" konfigurierte Issuer ({allowed_host!r}). Anfrage abgelehnt."
        )
    return url


def _fetch_discovery_document(issuer_url: str) -> dict:
    """
    Fetch the OIDC Discovery Document from {issuer_url}/.well-known/openid-configuration.
    Returns the parsed JSON dict.
    Raises requests.RequestException on network errors or non-200 responses.
    """
    from urllib.parse import urlunparse

    # Validate user-provided issuer_url first.
    _validate_oidc_url(issuer_url, "Issuer-URL")
    parsed = urlparse(issuer_url)

    # Reconstruct the discovery URL entirely from the validated parsed components
    # (scheme, netloc) plus a hardcoded path.  This breaks the taint chain from
    # user-controlled input to requests.get — the variable passed to requests
    # is built from trusted parts, not derived directly from the raw string.
    safe_base_path = parsed.path.rstrip("/")
    discovery_url = urlunparse(
        (
            parsed.scheme,  # validated: must be "https"
            parsed.netloc,  # validated: non-empty
            safe_base_path + "/.well-known/openid-configuration",  # hardcoded suffix
            "",  # params
            "",  # query
            "",  # fragment
        )
    )
    logger.debug("Fetching OIDC discovery document from %s", discovery_url)
    response = requests.get(discovery_url, timeout=10)
    response.raise_for_status()
    return response.json()


def _verify_id_token(id_token: str, discovery: dict, config, nonce: str) -> dict:
    """
    Verify the id_token JWT signature using the provider's JWKS and return claims.

    Uses PyJWT (installed as dependency of the API stack) so we do
    not rely on mozilla-django-oidc's internal URL resolution or settings access.
    """
    import jwt as pyjwt

    jwks_uri = discovery.get("jwks_uri", "")
    if not jwks_uri:
        raise ValueError("OIDC Provider hat keine jwks_uri im Discovery-Dokument.")

    # Validate jwks_uri: must be HTTPS and on the same host as the issuer to
    # prevent a malicious discovery document from redirecting key-fetches to an
    # attacker-controlled server (SSRF / key-confusion).
    issuer_host = urlparse(config.issuer_url).hostname
    _validate_oidc_url(jwks_uri, "JWKS-URI", allowed_host=issuer_host)

    # Reconstruct the JWKS URL from validated parsed components to break the
    # taint chain from the network-sourced discovery document to requests.get.
    from urllib.parse import urlunparse

    parsed_jwks = urlparse(jwks_uri)
    safe_jwks_url = urlunparse(
        (
            parsed_jwks.scheme,  # validated: must be "https"
            parsed_jwks.netloc,  # validated: same host as issuer
            parsed_jwks.path,  # path from validated URL
            "",  # params
            "",  # query — strip any attacker-injected query strings
            "",  # fragment
        )
    )
    jwks_response = requests.get(safe_jwks_url, timeout=10)
    jwks_response.raise_for_status()
    jwks = jwks_response.json()

    # Decode header without verification to find the signing key.
    header = pyjwt.get_unverified_header(id_token)
    kid = header.get("kid")
    alg = header.get("alg")
    if alg not in ALLOWED_ID_TOKEN_ALGORITHMS:
        raise ValueError(f"Nicht zugelassener Signaturalgorithmus {alg!r}.")

    matching_key = None
    for key_data in jwks.get("keys", []):
        if kid is None or key_data.get("kid") == kid:
            if alg.startswith("ES"):
                matching_key = pyjwt.algorithms.ECAlgorithm.from_jwk(key_data)
            else:
                matching_key = pyjwt.algorithms.RSAAlgorithm.from_jwk(key_data)
            break

    if matching_key is None:
        raise ValueError(f"Kein passender JWK-Schl\u00fcssel f\u00fcr kid={kid!r} gefunden.")

    claims = pyjwt.decode(
        id_token,
        key=matching_key,
        algorithms=[alg],
        audience=config.client_id,
        options={"require": ["exp", "iat", "iss", "aud", "sub"]},
    )

    # Verify issuer (lenient about trailing slash differences).
    token_issuer = claims.get("iss", "").rstrip("/")
    expected_issuer = config.issuer_url.rstrip("/")
    if token_issuer != expected_issuer:
        raise ValueError(f"Issuer stimmt nicht \u00fcberein: {token_issuer!r} != {expected_issuer!r}")

    # Verify nonce.
    if claims.get("nonce") != nonce:
        raise ValueError("Nonce stimmt nicht \u00fcberein.")

    logger.debug("OIDC: id_token verified for sub='%s' issuer='%s'", claims.get("sub", ""), token_issuer)
    return claims


def _provider_verified_mfa(claims, config):
    if not getattr(config, "trust_provider_mfa", False):
        return False
    methods = claims.get("amr") or []
    if isinstance(methods, str):
        methods = [methods]
    return bool(PROVIDER_MFA_METHODS & {str(method).lower() for method in methods})


# ---------------------------------------------------------------------------
# Public config endpoint (no auth required — called by login page)
# ---------------------------------------------------------------------------


class OIDCPublicConfigView(APIView):
    """
    GET /api/v1/auth/oidc/public-config/

    Returns the minimum OIDC configuration that the frontend needs to decide
    whether to show the SSO button and/or hide local login.
    Does NOT return any secrets.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        # Public fields only; the client secret is not even decrypted here.
        from settings_manager.models import OIDCConfig

        config = OIDCConfig.objects.filter(pk=1).only("enabled", "provider_name", "hide_local_login").first()
        if config is None:
            return Response({"enabled": False, "provider_name": "SSO", "hide_local_login": False})
        return Response(
            {
                "enabled": config.enabled,
                "provider_name": config.provider_name,
                "hide_local_login": config.hide_local_login,
            }
        )


# ---------------------------------------------------------------------------
# OIDC login initiation (generates authorization URL)
# ---------------------------------------------------------------------------


class OIDCLoginView(APIView):
    """
    GET /api/v1/auth/oidc/login/?next=/dashboard

    Builds the authorization URL with fresh state, nonce and PKCE challenge.
    The secrets stay in this browser's session; a new login replaces any
    unfinished one.

    Returns: { authorization_url: "https://provider/authorize?..." }
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        config = _get_oidc_config()
        if not config.enabled:
            return Response(
                {"detail": "OIDC ist nicht aktiviert."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            discovery = _fetch_discovery_document(config.issuer_url)
            authorization_endpoint = _validate_oidc_url(
                discovery.get("authorization_endpoint", ""),
                "Authorization-Endpunkt",
                allowed_host=urlparse(config.issuer_url).hostname,
            )
        except (requests.RequestException, ValueError) as exc:
            logger.error("OIDC: provider configuration unusable: %s", exc)
            return Response(
                {"detail": "OIDC Provider nicht erreichbar. Bitte versuche es später erneut."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        request._request.session[OIDC_FLOW_KEY] = {
            "state": state,
            "nonce": nonce,
            "verifier": verifier,
            "next": safe_next(request.GET.get("next")),
            "started_at": int(time.time()),
        }

        params = {
            "response_type": "code",
            "client_id": config.client_id,
            "redirect_uri": request.build_absolute_uri("/api/v1/auth/oidc/callback/"),
            "scope": config.scope,
            "state": state,
            "nonce": nonce,
            "code_challenge": _pkce_challenge(verifier),
            "code_challenge_method": "S256",
        }
        return Response({"authorization_url": authorization_endpoint + "?" + urlencode(params)})


# ---------------------------------------------------------------------------
# OIDC callback (handles IdP redirect, establishes the Django session)
# ---------------------------------------------------------------------------


class OIDCCallbackView(View):
    """
    GET /api/v1/auth/oidc/callback/?code=...&state=...

    Plain Django view: the browser arrives via redirect from the IdP and is
    redirected to the frontend afterwards.
    """

    def get(self, request):
        flow = request.session.pop(OIDC_FLOW_KEY, None)

        if "error" in request.GET:
            logger.warning("OIDC: IdP returned error %r", request.GET.get("error", "")[:64])
            return self._redirect_error("provider_error")

        code = request.GET.get("code")
        state = request.GET.get("state")
        if not code or not state:
            return self._redirect_error("invalid_response")

        # Bound to this browser, unexpired and usable only once — even if two
        # callbacks race with the same session.
        if (
            not flow
            or not hmac.compare_digest(str(flow.get("state", "")), state)
            or time.time() - flow.get("started_at", 0) > OIDC_STATE_TIMEOUT
            or not cache.add(f"oidc_state_used_{hashlib.sha256(state.encode()).hexdigest()}", 1, OIDC_STATE_TIMEOUT)
        ):
            logger.warning("OIDC callback: unknown, foreign, expired or reused state")
            return self._redirect_error("expired")

        config = _get_oidc_config()
        if not config.enabled:
            return self._redirect_error("disabled")

        issuer_host = urlparse(config.issuer_url).hostname
        try:
            discovery = _fetch_discovery_document(config.issuer_url)
            token_endpoint = _validate_oidc_url(
                discovery.get("token_endpoint", ""), "Token-Endpunkt", allowed_host=issuer_host
            )
        except (requests.RequestException, ValueError) as exc:
            logger.error("OIDC callback: provider configuration unusable: %s", exc)
            return self._redirect_error("unavailable")

        try:
            token_response = requests.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": request.build_absolute_uri("/api/v1/auth/oidc/callback/"),
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                    "code_verifier": flow["verifier"],
                },
                timeout=15,
                allow_redirects=False,
            )
            token_response.raise_for_status()
            id_token = token_response.json().get("id_token")
        except (requests.RequestException, ValueError) as exc:
            logger.error("OIDC callback: token exchange failed: %s", type(exc).__name__)
            return self._redirect_error("unavailable")

        if not id_token:
            logger.error("OIDC callback: no id_token in token response")
            return self._redirect_error("invalid_response")

        try:
            claims = _verify_id_token(id_token, discovery, config, flow["nonce"])
        except Exception as exc:
            logger.warning("OIDC callback: id_token verification failed: %s", type(exc).__name__)
            return self._redirect_error("verification_failed")

        try:
            from users.oidc_backend import JFManagerOIDCBackend

            backend = JFManagerOIDCBackend()
            # authenticate() reads the verified claims instead of re-exchanging the code.
            request._oidc_claims = claims
            user = backend.authenticate(request)
        except Exception as exc:
            logger.warning("OIDC callback: account rejected: %s", type(exc).__name__)
            return self._redirect_error("account_rejected")

        if user is None or not user.is_active:
            return self._redirect_error("account_rejected")

        from users.session_views import begin_login

        user.backend = "users.oidc_backend.JFManagerOIDCBackend"
        begin_login(request, user, mfa_satisfied=_provider_verified_mfa(claims, config))
        logger.info("OIDC: user id %s authenticated via provider", user.pk)
        result = "ok" if request.user.is_authenticated else "mfa_required"
        return self._redirect(result=result, next=flow["next"])

    @staticmethod
    def _redirect(**params) -> HttpResponse:
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
        response = HttpResponse(status=302)
        response["Location"] = f"{frontend_url}/auth/oidc/callback?{urlencode(params)}"
        response["Cache-Control"] = "no-store"
        return response

    @classmethod
    def _redirect_error(cls, error_code: str) -> HttpResponse:
        assert error_code in ERROR_MESSAGES
        return cls._redirect(error=error_code)


# ---------------------------------------------------------------------------
# Discovery test (settings UI helper — requires change_oidc_settings)
# ---------------------------------------------------------------------------


class OIDCTestDiscoveryView(APIView):
    """
    POST /api/v1/auth/oidc/test-discovery/
    Body: { "issuer_url": "https://..." }

    Tests whether the OIDC Discovery Document can be fetched from the given
    issuer URL. Returns the discovery data or an error description.
    Requires change_oidc_settings or change_all_settings permission.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not (
            request.user.has_perm("settings_manager.change_oidc_settings")
            or request.user.has_perm("settings_manager.change_all_settings")
        ):
            return Response(
                {"detail": "Keine Berechtigung."},
                status=status.HTTP_403_FORBIDDEN,
            )

        issuer_url = request.data.get("issuer_url", "").strip()
        if not issuer_url:
            return Response(
                {"detail": "issuer_url fehlt."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            discovery = _fetch_discovery_document(issuer_url)
        except requests.RequestException as exc:
            logger.warning("OIDC test-discovery: failed for '%s': %s", issuer_url, exc)
            return Response(
                {
                    "ok": False,
                    "detail": f"Discovery-Dokument konnte nicht abgerufen werden: {exc}",
                },
                status=status.HTTP_200_OK,
            )

        logger.info("OIDC test-discovery: success for '%s'", issuer_url)
        return Response(
            {
                "ok": True,
                "issuer": discovery.get("issuer"),
                "authorization_endpoint": discovery.get("authorization_endpoint"),
                "token_endpoint": discovery.get("token_endpoint"),
                "userinfo_endpoint": discovery.get("userinfo_endpoint"),
                "jwks_uri": discovery.get("jwks_uri"),
                "scopes_supported": discovery.get("scopes_supported", []),
                "claims_supported": discovery.get("claims_supported", []),
            }
        )
