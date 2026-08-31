"""Authenticated Garmin Connect client, built from env vars with token caching."""

from __future__ import annotations

import os
from pathlib import Path

from garminconnect import Garmin

TOKEN_STORE = Path.home() / ".garminconnect"


def _prompt_mfa() -> str:
    return input("Enter the Garmin Connect MFA code sent to you: ").strip()


def get_client() -> Garmin:
    """Return an authenticated Garmin Connect client.

    Reads GARMIN_EMAIL / GARMIN_PASSWORD from the environment (see .env.example).
    ``login()`` reuses a cached OAuth token from ~/.garminconnect when present
    and only falls back to a full credential login (prompting for MFA if
    needed) when there's no valid cached session.
    """
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")

    client = Garmin(email=email, password=password, prompt_mfa=_prompt_mfa)
    client.login(str(TOKEN_STORE))
    return client
