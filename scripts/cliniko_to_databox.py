"""
Pulls activity from Cliniko and pushes daily metrics to Databox.

TEMPORARY TEST MODE IS ACTIVE: this version captures TODAY's activity
instead of yesterday's, to let you test with same-day data. See the two
lines marked TEMPORARY below - delete them when you're done testing.

Metrics pushed:
  cliniko_new_patients        - new patients in the window
  cliniko_appointments_booked - appointments created in the window
  cliniko_appointments_cancelled - appointments cancelled in the window
  cliniko_invoice_revenue     - total invoiced amount
  cliniko_invoices_issued     - number of invoices issued

Required environment variables / GitHub secrets:
  CLINIKO_API_KEY   - from Cliniko: My Info > Manage API keys
  CLINIKO_SHARD     - the subdomain in your Cliniko URL, e.g. "api.au5"
  DATABOX_TOKEN     - Databox push token (Data Manager > Active data connections)
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import requests

CLINIKO_API_KEY = os.environ["CLINIKO_API_KEY"]
CLINIKO_SHARD = os.environ["CLINIKO_SHARD"]
DATABOX_TOKEN = os.environ["DATABOX_TOKEN"]

BASE_URL = f"https://{CLINIKO_SHARD}.cliniko.com/v1"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "CRM-to-Databox-Sync (you@example.com)",
}
AUTH = (CLINIKO_API_KEY, "")

today = datetime.now(timezone.utc).date()
yesterday = today - timedelta(days=1)

# TEMPORARY TEST MODE: shift the window forward one day to capture TODAY's
# activity instead of yesterday's. Delete these two lines when done testing.
yesterday = today
today = today + timedelta(days=1)

ts_start = f"{yesterday.isoformat()}T00:00:00Z"
ts_end = f"{today.isoformat()}T00:00:00Z"


def cliniko_get_all(path, filters=None):
    params = [("q[]", f) for f in (filters or [])]
    params.append(("per_page", 100))

    results = []
    url = f"{BASE_URL}/{path}"
    while url:
        resp = requests.get(url, headers=HEADERS, auth=AUTH, params=params)
        resp.raise_for_status()
        data = resp.json()
        key = [k for k in data.keys() if k != "links" and k != "total_entries"][0]
        results.extend(data[key])
        url = data.get("links", {}).get("next")
        params = None
    return results


def get_new_patients():
    patients = cliniko_get_all(
        "patients",
        [f"created_at:>={ts_start}", f"created_at:<{ts_end}"],
    )
    return len(patients)


def get_appointments():
    booked = cliniko_get_all(
        "individual_appointments",
        [f"created_at:>={ts_start}", f"created_at:<{ts_end}"],
    )
    cancelled = cliniko_get_all(
        "individual_appointments",
        [f"cancelled_at:>={ts_start}", f"cancelled_at:<{ts_end}"],
    )
    return len(booked), len(cancelled)


def
