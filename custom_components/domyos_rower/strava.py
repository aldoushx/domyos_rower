"""Minimal Strava API client: OAuth tokens, upload of a TCX/FIT/GPX file, sport type.

Uses a "personal" API application (the user's own client id/secret), no HA import.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import re
import time
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import aiohttp

STRAVA_BASE = "https://www.strava.com"
REDIRECT_URI = "http://localhost"
SCOPE = "activity:write"
TOKEN_MARGIN = 120  # refresh the token this many seconds before it expires
POLL_INTERVAL = 1.5  # seconds between two checks of the upload processing status
POLL_TIMEOUT = 90.0


class StravaError(Exception):
    """Anything that goes wrong talking to Strava."""


class StravaAuthError(StravaError):
    """Bad credentials / code / revoked access."""


def authorize_url(client_id: str, base: str | None = None) -> str:
    query = urlencode(
        {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "approval_prompt": "force",
            "scope": SCOPE,
        }
    )
    return f"{base or STRAVA_BASE}/oauth/authorize?{query}"


def extract_code(text: str) -> str:
    """Accepts the bare code or the whole http://localhost/?code=... address."""
    text = (text or "").strip()
    if "code=" in text:
        query = parse_qs(urlparse(text).query)
        if query.get("code"):
            return query["code"][0]
        match = re.search(r"code=([^&\s]+)", text)
        if match:
            return match.group(1)
    return text


def _message(data: Any, status: int) -> str:
    if isinstance(data, dict):
        errors = data.get("errors")
        if errors:
            return "; ".join(
                f"{e.get('resource', '?')}: {e.get('field', '?')} {e.get('code', '?')}"
                for e in errors
                if isinstance(e, dict)
            )
        if data.get("message"):
            return str(data["message"])
        if data.get("error"):
            return str(data["error"])
    return f"HTTP {status}"


class StravaClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        client_id: str,
        client_secret: str,
        tokens: dict | None = None,
        *,
        base: str | None = None,
        token_saved: Callable[[dict], Awaitable[None] | None] | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._session = session
        self._client_id = client_id
        self._client_secret = client_secret
        self.tokens = dict(tokens or {})
        self._base = base or STRAVA_BASE
        self._token_saved = token_saved
        self._clock = clock

    # ------------------------------------------------------------------ tokens
    async def _token_request(self, form: dict) -> dict:
        form = {"client_id": self._client_id, "client_secret": self._client_secret, **form}
        try:
            async with self._session.post(f"{self._base}/oauth/token", data=form) as resp:
                data = await resp.json(content_type=None)
                status = resp.status
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise StravaError(f"cannot reach Strava: {err}") from err
        if status != 200 or not isinstance(data, dict) or "access_token" not in data:
            raise StravaAuthError(_message(data, status))
        tokens = {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", self.tokens.get("refresh_token")),
            "expires_at": int(data.get("expires_at", self._clock() + 3600)),
        }
        athlete = data.get("athlete") or self.tokens.get("athlete")
        if athlete:
            tokens["athlete"] = {
                "id": athlete.get("id"),
                "name": " ".join(
                    x for x in (athlete.get("firstname"), athlete.get("lastname")) if x
                ),
            }
        self.tokens = tokens
        if self._token_saved:
            result = self._token_saved(dict(tokens))
            if asyncio.iscoroutine(result):
                await result
        return tokens

    async def exchange_code(self, code: str) -> dict:
        return await self._token_request({"code": code, "grant_type": "authorization_code"})

    async def _access_token(self, force: bool = False) -> str:
        if not self.tokens.get("refresh_token"):
            raise StravaAuthError("Strava is not authorised yet")
        if force or self._clock() >= self.tokens.get("expires_at", 0) - TOKEN_MARGIN:
            await self._token_request(
                {"grant_type": "refresh_token", "refresh_token": self.tokens["refresh_token"]}
            )
        return self.tokens["access_token"]

    async def _request(self, method: str, path: str, **kwargs: Any) -> tuple[int, Any]:
        """Authenticated call; refreshes the token once if Strava answers 401."""
        for attempt in (1, 2):
            token = await self._access_token(force=attempt == 2)
            headers = {"Authorization": f"Bearer {token}"}
            try:
                data = kwargs.get("data")
                if isinstance(data, aiohttp.FormData):  # a FormData can't be sent twice
                    kwargs["data"] = self._rebuild(data)
                async with self._session.request(
                    method, f"{self._base}{path}", headers=headers, **kwargs
                ) as resp:
                    payload = await resp.json(content_type=None)
                    status = resp.status
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                raise StravaError(f"cannot reach Strava: {err}") from err
            if status == 401 and attempt == 1:
                continue
            if status == 401:
                raise StravaAuthError(_message(payload, status))
            if status == 429:
                raise StravaError("Strava rate limit reached, try again in a few minutes")
            return status, payload
        raise StravaError("unreachable")  # pragma: no cover

    @staticmethod
    def _rebuild(form: aiohttp.FormData) -> aiohttp.FormData:
        return form

    # ------------------------------------------------------------------ upload
    async def upload(
        self,
        content: bytes,
        filename: str,
        *,
        data_type: str = "tcx",
        name: str | None = None,
        description: str | None = None,
        trainer: bool = True,
        external_id: str | None = None,
    ) -> int:
        """Queue a file for processing. Returns the upload id."""

        def build() -> aiohttp.FormData:
            form = aiohttp.FormData()
            form.add_field("file", content, filename=filename, content_type="application/octet-stream")
            form.add_field("data_type", data_type)
            if name:
                form.add_field("name", name)
            if description:
                form.add_field("description", description)
            form.add_field("trainer", "1" if trainer else "0")
            if external_id:
                form.add_field("external_id", external_id)
            return form

        status, payload = await self._request("POST", "/api/v3/uploads", data=build())
        if status not in (200, 201) or not isinstance(payload, dict) or "id" not in payload:
            raise StravaError(f"upload refused: {_message(payload, status)}")
        if payload.get("error"):
            raise StravaError(f"upload refused: {payload['error']}")
        return int(payload["id"])

    async def wait_for_activity(
        self, upload_id: int, *, timeout: float | None = None, interval: float | None = None
    ) -> int:
        """Poll until Strava has processed the file. Returns the activity id."""
        timeout = POLL_TIMEOUT if timeout is None else timeout
        interval = POLL_INTERVAL if interval is None else interval
        deadline = self._clock() + timeout
        while True:
            status, payload = await self._request("GET", f"/api/v3/uploads/{upload_id}")
            if status == 200 and isinstance(payload, dict):
                if payload.get("error"):
                    raise StravaError(f"Strava rejected the file: {payload['error']}")
                if payload.get("activity_id"):
                    return int(payload["activity_id"])
            elif status >= 400:
                raise StravaError(f"cannot read upload status: {_message(payload, status)}")
            if self._clock() >= deadline:
                raise StravaError("Strava is still processing the file, check your Strava feed later")
            await asyncio.sleep(interval)

    async def set_sport_type(self, activity_id: int, sport_type: str) -> None:
        status, payload = await self._request(
            "PUT", f"/api/v3/activities/{activity_id}", json={"sport_type": sport_type}
        )
        if status != 200:
            raise StravaError(f"cannot set the activity type: {_message(payload, status)}")

    async def upload_activity(
        self,
        content: bytes,
        filename: str,
        *,
        name: str,
        description: str,
        sport_type: str = "Rowing",
        external_id: str | None = None,
        poll_interval: float | None = None,
        timeout: float | None = None,
    ) -> dict:
        """Upload, wait for processing, then set the sport type. Returns ids and URL."""
        upload_id = await self.upload(
            content,
            filename,
            name=name,
            description=description,
            trainer=True,
            external_id=external_id,
        )
        activity_id = await self.wait_for_activity(upload_id, timeout=timeout, interval=poll_interval)
        result = {
            "upload_id": upload_id,
            "activity_id": activity_id,
            "url": f"https://www.strava.com/activities/{activity_id}",
            "sport_type_set": True,
        }
        try:
            await self.set_sport_type(activity_id, sport_type)
        except StravaError as err:  # the activity exists: don't fail the whole upload
            result["sport_type_set"] = False
            result["warning"] = str(err)
        return result
