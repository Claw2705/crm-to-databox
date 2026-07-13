"""
Template: pulls daily activity from mywellness (Technogym) and pushes metrics to Databox.

IMPORTANT: Unlike Cliniko, mywellness's server-to-server API is NOT self-serve.
You need to request access first:
  1. Contact Technogym (your account rep, or aus.cloudsupport@technogym.com-style
     regional contact) and ask for the mywellness cloud "server to server" API.
  2. They'll send an API Agreement to sign.
  3. Once approved (Technogym partners quote ~3 working days to a few weeks),
     you'll get real credentials and the exact endpoint paths for your facility.
  4. Full reference once you're approved: https://apidocs.mywellness.com/

Because the concrete endpoints depend on what Technogym provisions for your
facility, the calls below are placeholders — swap `FACILITY_ENDPOINT` and the
response field names for what's in the docs/Postman collection they give you.

Required environment variables / GitHub secrets (names you'll adjust once you
have real credentials):
  MYWELLNESS_API_KEY
  MYWELLNESS_FACILITY_ID
  DATABOX_TOKEN
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import requests

MYWELLNESS_API_KEY = os.environ["MYWELLNESS_API_KEY"]
MYWELLNESS_FACILITY_ID = os.environ["MYWELLNESS_FACILITY_ID"]
DATABOX_TOKEN = os.environ["DATABOX_TOKEN"]

# Placeholder base URL - replace with what Technogym provisions for you.
BASE_URL = "https://api.mywellness.com"

HEADERS = {
    "Authorization": f"Bearer {MYWELLNESS_API_KEY}",
    "Accept": "application/json",
}

today = datetime.now(timezone.utc).date()
yesterday = today - timedelta(days=1)


def get_active_members():
    # Placeholder endpoint - confirm the real path in your API agreement docs
    resp = requests.get(
        f"{BASE_URL}/facilities/{MYWELLNESS_FACILITY_ID}/members",
        headers=HEADERS,
        params={"status": "active"},
    )
    resp.raise_for_status()
    return len(resp.json().get("members", []))


def get_class_attendance():
    # Placeholder endpoint
    resp = requests.get(
        f"{BASE_URL}/facilities/{MYWELLNESS_FACILITY_ID}/classes/attendance",
        headers=HEADERS,
        params={"date": yesterday.isoformat()},
    )
    resp.raise_for_status()
    return resp.json().get("total_attendance", 0)


def push_to_databox(metrics):
    resp = requests.post(
        "https://push.databox.com/data",
        auth=(DATABOX_TOKEN, ""),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/vnd.databox.v2+json",
        },
        json=metrics,
    )
    resp.raise_for_status()
    print("Pushed to Databox:", resp.json())


def main():
    date_str = yesterday.isoformat()

    active_members = get_active_members()
    attendance = get_class_attendance()

    metrics = [
        {"key": "mywellness_active_members", "value": active_members, "date": date_str},
        {"key": "mywellness_class_attendance", "value": attendance, "date": date_str},
    ]

    print(f"Metrics for {date_str}: {metrics}")
    push_to_databox(metrics)


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print(f"HTTP error: {e.response.status_code} {e.response.text}", file=sys.stderr)
        sys.exit(1)
