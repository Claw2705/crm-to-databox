"""
Pulls yesterday's activity from Cliniko and pushes daily metrics to Databox.

Metrics pushed:
  cliniko_new_patients        - patients created yesterday
  cliniko_appointments_booked - individual appointments created yesterday
  cliniko_appointments_cancelled - appointments cancelled yesterday
  cliniko_invoice_revenue     - total invoiced amount (issued yesterday)
  cliniko_invoices_issued     - number of invoices issued yesterday

Required environment variables / GitHub secrets:
  CLINIKO_API_KEY   - from Cliniko: My Info > Manage API keys
  CLINIKO_SHARD     - the subdomain in your Cliniko URL, e.g. "api.au4" or "api.uk2"
                       (find it in Settings > API Keys, it's shown in the base URL)
  DATABOX_TOKEN     - Databox push token (Data Manager > Active data connections)
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import requests

CLINIKO_API_KEY = os.environ["CLINIKO_API_KEY"]
CLINIKO_SHARD = os.environ["CLINIKO_SHARD"]  # e.g. "api.au4"
DATABOX_TOKEN = os.environ["DATABOX_TOKEN"]

BASE_URL = f"https://{CLINIKO_SHARD}.cliniko.com/v1"
HEADERS = {
    "Accept": "application/json",
    # Cliniko requires a descriptive User-Agent identifying your app + contact email
    "User-Agent": "CRM-to-Databox-Sync (you@example.com)",
}
AUTH = (CLINIKO_API_KEY, "")  # HTTP Basic auth, password left blank

# Yesterday's date window, UTC. Adjust timezone as needed for your clinic.
today = datetime.now(timezone.utc).date()
yesterday = today - timedelta(days=1)
start = f"{yesterday.isoformat()}T00:00:00Z"
end = f"{today.isoformat()}T00:00:00Z"


def cliniko_get_all(path, params=None):
    """Paginate through a Cliniko endpoint and return the combined list of records."""
    params = dict(params or {})
    params["per_page"] = 100
    results = []
    url = f"{BASE_URL}/{path}"
    while url:
        resp = requests.get(url, headers=HEADERS, auth=AUTH, params=params)
        resp.raise_for_status()
        data = resp.json()
        # Cliniko wraps results under the resource name, e.g. {"patients": [...]}
        key = [k for k in data.keys() if k != "links" and k != "total_entries"][0]
        results.extend(data[key])
        url = data.get("links", {}).get("next")
        params = None  # params are baked into the "next" link already
    return results


def get_new_patients():
    patients = cliniko_get_all(
        "patients",
        {"q[]": f"created_at:>={start},created_at:<{end}"},
    )
    return len(patients)


def get_appointments():
    booked = cliniko_get_all(
        "individual_appointments",
        {"q[]": f"created_at:>={start},created_at:<{end}"},
    )
    cancelled = cliniko_get_all(
        "individual_appointments",
        {"q[]": f"cancelled_at:>={start},cancelled_at:<{end}"},
    )
    return len(booked), len(cancelled)


def get_invoices():
    invoices = cliniko_get_all(
        "invoices",
        {"q[]": f"issue_date:>={yesterday.isoformat()},issue_date:<={yesterday.isoformat()}"},
    )
    revenue = sum(float(inv.get("total_including_tax", 0) or 0) for inv in invoices)
    return len(invoices), revenue


def push_to_databox(metrics):
    """metrics: list of {"key": ..., "value": ..., "date": ...}"""
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

    new_patients = get_new_patients()
    booked, cancelled = get_appointments()
    invoice_count, revenue = get_invoices()

    metrics = [
        {"key": "cliniko_new_patients", "value": new_patients, "date": date_str},
        {"key": "cliniko_appointments_booked", "value": booked, "date": date_str},
        {"key": "cliniko_appointments_cancelled", "value": cancelled, "date": date_str},
        {"key": "cliniko_invoices_issued", "value": invoice_count, "date": date_str},
        {"key": "cliniko_invoice_revenue", "value": round(revenue, 2), "date": date_str},
    ]

    print(f"Metrics for {date_str}: {metrics}")
    push_to_databox(metrics)


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print(f"HTTP error: {e.response.status_code} {e.response.text}", file=sys.stderr)
        sys.exit(1)
