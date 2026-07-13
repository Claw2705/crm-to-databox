# CRM → Databox sync (via GitHub Actions)

Pulls daily metrics from Cliniko (and, once you have API access, mywellness)
and pushes them into Databox as custom metrics — no Zapier/Make needed.

Mindbody is **not** included here because Databox already has a native,
one-click Mindbody connector (Data Manager > + New Data Source > Mindbody).
Use that instead of scripting it.

## How it works

- `scripts/cliniko_to_databox.py` — calls the Cliniko REST API for
  yesterday's new patients, appointments booked/cancelled, and invoice
  revenue, then pushes those as metrics to Databox.
- `scripts/mywellness_to_databox.py` — same idea for mywellness, but it's a
  **template**. mywellness's server-to-server API isn't self-serve; you need
  to request an API Agreement from Technogym first (see comments in the
  file). Fill in the real endpoints once you're approved.
- `.github/workflows/sync-to-databox.yml` — GitHub Actions workflow that runs
  both scripts once a day (cron) and can also be triggered manually from the
  Actions tab.

## Setup

1. **Create the repo**: push this folder to a new GitHub repository.

2. **Get a Databox push token**: in Databox, go to *Data Manager > Active
   data connections*, grab your API token (or create a new custom Data
   Source and use its token so Cliniko/mywellness metrics are grouped
   separately from other sources).

3. **Get a Cliniko API key**: in Cliniko, go to *My Info > Manage API keys*.
   Also note your shard — it's the subdomain in your Cliniko API base URL
   (e.g. `api.au4`, `api.uk2`, `api.eu2`) — check *Settings > API Keys* for
   the exact value shown in the example curl command there.

4. **Add GitHub Secrets**: in your repo, go to *Settings > Secrets and
   variables > Actions* and add:
   - `CLINIKO_API_KEY`
   - `CLINIKO_SHARD`
   - `DATABOX_TOKEN`
   - (later) `MYWELLNESS_API_KEY`, `MYWELLNESS_FACILITY_ID`

5. **Test it manually**: go to the *Actions* tab in GitHub, select "Sync CRM
   data to Databox", and click *Run workflow*. Check the logs — you should
   see the metrics printed, then a success response from Databox.

6. **Check Databox**: the pushed metrics (`cliniko_new_patients`,
   `cliniko_appointments_booked`, `cliniko_appointments_cancelled`,
   `cliniko_invoices_issued`, `cliniko_invoice_revenue`) will show up under
   your custom Data Source. Build Datacards from them like any other metric.

7. **mywellness**: once Technogym approves your API Agreement, replace the
   placeholder endpoints in `scripts/mywellness_to_databox.py` with the real
   ones from your docs/Postman collection, add the two mywellness secrets,
   and the `sync-mywellness` job in the workflow will start working too.

## Adjusting the schedule

The workflow runs at 05:00 UTC daily. Edit the `cron` line in
`.github/workflows/sync-to-databox.yml` to change that — cron is always in
UTC regardless of your local timezone.

## Adding more metrics

Add a new function to the relevant script (e.g. `get_treatment_notes_count`)
following the same pattern: query the API, count/aggregate, append a
`{"key": ..., "value": ..., "date": ...}` dict to the `metrics` list before
the `push_to_databox(metrics)` call.
