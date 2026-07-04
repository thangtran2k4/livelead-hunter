from __future__ import annotations

import os
from typing import Any

import requests


def send_telegram_message(message: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False

    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": message},
        timeout=20,
    )
    response.raise_for_status()
    return True


def send_slack_message(message: str) -> bool:
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return False

    response = requests.post(webhook_url, json={"text": message}, timeout=20)
    response.raise_for_status()
    return True


def notify(message: str) -> dict[str, bool]:
    results = {
        "telegram": False,
        "slack": False,
    }
    try:
        results["telegram"] = send_telegram_message(message)
    except Exception:
        results["telegram"] = False

    try:
        results["slack"] = send_slack_message(message)
    except Exception:
        results["slack"] = False

    return results
