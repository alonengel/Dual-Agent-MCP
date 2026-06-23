"""Gmail API emailer for the automated end-of-match report.

Uses OAuth token-based auth (preferred over username/password, as the lecture
explains). Credentials come from files referenced by environment variables and are
never committed. If credentials are missing the call degrades gracefully.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from email.mime.text import MIMEText
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from copthief.shared.gatekeeper import ApiGatekeeper

_log = logging.getLogger("copthief.email")
# Matches the course Gmail-API guide: gmail.modify covers sending/drafting.
_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def _load_credentials():
    """Build Google OAuth credentials, refreshing or running the consent flow."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    token_file = Path(os.environ.get("GMAIL_TOKEN_FILE", "token.json"))
    secret_file = Path(os.environ.get("GMAIL_CLIENT_SECRET_FILE", "credentials.json"))
    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), _SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), _SCOPES)
            creds = flow.run_local_server(port=0)
        token_file.write_text(creds.to_json())
    return creds


def send_report_email(to_addr: str, subject: str, body_json: dict,
                      gate: ApiGatekeeper | None = None) -> bool:
    """Send the JSON report via Gmail. Returns False (no raise) on missing setup.

    The Gmail API call is routed through the shared gatekeeper when provided, so
    this external call obeys the same throttle/retry policy as the LLM calls.
    """
    try:
        from googleapiclient.discovery import build

        creds = _load_credentials()
        service = build("gmail", "v1", credentials=creds)
        message = MIMEText(json.dumps(body_json, ensure_ascii=False), "plain", "utf-8")
        message["to"] = to_addr
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        def _send() -> None:
            service.users().messages().send(userId="me", body={"raw": raw}).execute()

        if gate is not None:
            gate.execute(_send)
        else:
            _send()
        _log.info("report email sent to %s", to_addr)
        return True
    except Exception as exc:  # noqa: BLE001 - email must never crash the pipeline
        _log.warning("email skipped (%s); report still saved to disk", exc)
        return False
