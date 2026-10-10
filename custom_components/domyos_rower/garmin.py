"""Optional upload of a session file to Garmin Connect, through the `garminconnect` library.

This relies on an unofficial login (Garmin offers no public upload API for individuals): it can
break when Garmin changes its sign-in. Only the e-mail and the library's session tokens are
kept (never the password). Everything here is synchronous: call it from an executor.
"""
from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

GARMIN_REQUIREMENT = "garminconnect==0.3.17"


class GarminError(Exception):
    """Anything that stops the upload (message is shown to the user)."""


class GarminAuthError(GarminError):
    """Sign-in refused or session expired: the account has to be linked again."""


def _lib():
    try:
        import garminconnect  # noqa: PLC0415
    except ImportError as err:  # pragma: no cover - depends on the installation
        raise GarminError(
            "La bibliothèque garminconnect n'est pas installée "
            f"(pip install {GARMIN_REQUIREMENT})."
        ) from err
    return garminconnect


def start_login(email: str, password: str) -> tuple[Any, bool]:
    """Sign in. Returns (api, needs_mfa); with needs_mfa the code goes to finish_mfa()."""
    lib = _lib()
    api = lib.Garmin(email=email, password=password, return_on_mfa=True)
    try:
        mfa_status, _ = api.login()
    except lib.GarminConnectAuthenticationError as err:
        raise GarminAuthError("Garmin a refusé l'e-mail ou le mot de passe.") from err
    except lib.GarminConnectTooManyRequestsError as err:
        raise GarminError("Garmin limite les tentatives de connexion : réessaie plus tard.") from err
    except Exception as err:  # noqa: BLE001
        raise GarminError(f"Connexion à Garmin impossible : {err}") from err
    return api, bool(mfa_status)


def finish_mfa(api: Any, code: str) -> None:
    lib = _lib()
    try:
        api.resume_login({}, code.strip())
    except lib.GarminConnectAuthenticationError as err:
        raise GarminAuthError("Code de vérification refusé.") from err
    except Exception as err:  # noqa: BLE001
        raise GarminError(f"Vérification impossible : {err}") from err


def dump_tokens(api: Any) -> str:
    return api.client.dumps()


def upload_file(tokens: str, path: str) -> tuple[dict, str]:
    """Upload `path` (FIT/TCX/GPX). Returns (result, refreshed tokens to store)."""
    lib = _lib()
    api = lib.Garmin()
    try:
        api.login(tokenstore=tokens)
    except lib.GarminConnectAuthenticationError as err:
        raise GarminAuthError(
            "La session Garmin a expiré : relie de nouveau ton compte dans les options."
        ) from err
    except Exception as err:  # noqa: BLE001
        raise GarminError(f"Connexion à Garmin impossible : {err}") from err
    try:
        raw = api.upload_activity(path)
    except lib.GarminConnectAuthenticationError as err:
        raise GarminAuthError(
            "La session Garmin a expiré : relie de nouveau ton compte dans les options."
        ) from err
    except lib.GarminConnectTooManyRequestsError as err:
        raise GarminError("Garmin limite les requêtes : réessaie plus tard.") from err
    except Exception as err:  # noqa: BLE001
        text = str(err)
        if "409" in text or "uplicate" in text:
            raise GarminError("Garmin indique que cette séance est déjà importée.") from err
        raise GarminError(f"Envoi vers Garmin impossible : {text}") from err
    result: dict = {}
    try:
        status = raw.get("detailedImportResult", {}) if isinstance(raw, dict) else {}
        failures = status.get("failures") or []
        successes = status.get("successes") or []
        if failures and not successes:
            msgs = "; ".join(
                str(m.get("content", m)) for f in failures for m in (f.get("messages") or [f])
            )
            if "uplicate" in msgs or "409" in msgs:
                raise GarminError("Garmin indique que cette séance est déjà importée.")
            raise GarminError(f"Garmin a refusé le fichier : {msgs or failures}")
        if successes:
            result["activity_id"] = successes[0].get("internalId")
    except AttributeError:
        pass
    try:
        refreshed = api.client.dumps()
    except Exception:  # noqa: BLE001
        refreshed = tokens
    return result, refreshed
