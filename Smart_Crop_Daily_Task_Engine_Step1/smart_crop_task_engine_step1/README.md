# Smart Crop Advisory — Daily Task Engine (Step 1)

An integrated FastAPI and Flutter crop-advisory application for **tomato and chilli**. It reuses the existing farmer accounts, crop cycles, task generator, SQLite database, and Flutter app.

## Crop age convention

Crop age uses calendar-day difference: the planting/transplanting date is day 0, the next date is day 1, and dates before planting have no crop age. Schedule day ranges are inclusive. The crop cycle's stored `planting_date` is the reference date; `planting_method` does not shift the count.

## Requirements
- Python 3.11 or 3.12 recommended
- VS Code
- Terminal / PowerShell

## Windows setup

Open this folder in VS Code, then run in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

If PowerShell blocks activation, run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

If Python 3.12 is not installed, use your installed Python version (3.11+).

## Verify it works
- Home: http://127.0.0.1:8000/
- Health: http://127.0.0.1:8000/api/v1/health
- Interactive API docs: http://127.0.0.1:8000/docs

Expected health response:
```json
{"status": "healthy"}
```

## Run tests
In a second terminal with the virtual environment activated:
```powershell
pytest -q
```

## Automatic daily monitoring tasks
The API lifespan starts an APScheduler job that creates daily monitoring tasks at **06:00
Asia/Kolkata**. The job gets the date in India time, processes active crop cycles whose planting
date has arrived, opens its own database session, and logs the date, cycles processed, tasks
created, and cycle errors. Each cycle commits independently, so one failed cycle does not block
other cycles. Existing task generation eligibility and verification checks remain in force.

Run one job immediately from this directory without making an HTTP request:

```powershell
.\.venv\Scripts\python.exe -c "from app.services.daily_task_scheduler import run_daily_task_job; print(run_daily_task_job())"
```

To exercise a chosen date in a test or local script, call
`run_daily_task_job(date(YYYY, MM, DD))` directly. The job can be run more than once for the
same date; existing monitoring tasks remain unchanged, including completed tasks.

Install dependencies and start one or more API workers on a single host:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 1
```

For local development, use `python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload`.
An OS-level lock in the host temp directory elects one worker as the scheduler owner; other
workers log that the scheduler is owned elsewhere. The lock is released on normal shutdown and
automatically by the OS if a worker exits. This safeguard is host-local, so the supported
multi-worker deployment is multiple workers sharing the same local database on one host. For
multiple hosts, run the API with the scheduler enabled on only one host (and keep that host
pointed at the shared database); APScheduler's in-memory job store is not a distributed scheduler.

Verify the generated tasks in Swagger at `/docs`: log in at `/api/v1/auth/login`, authorize with
the returned bearer token, then call `GET /api/v1/tasks?task_date=YYYY-MM-DD`. No public scheduler
trigger endpoint is exposed.

## Integrated capabilities and source review

- Authenticated task, upcoming-task, status-history, crop-observation, crop-stage, weather, and disease-model-status APIs are available. Task completion and reopen actions append history; observations can reference a crop-cycle task and optional photo.
- The Flutter advisory, alerts, history, and scan screens use authenticated APIs. Weather is labeled as observed, stale, or unavailable; it is context and is not turned into unsupported action thresholds.
- Excel imports preserve the raw cells from `Prevention Measures`, `Pesticide - Diseases`, and `Pesticide - Pests` in review-pending agricultural source records. The chilli PDF importer preserves extracted page text for review. Imported rows remain inactive.
- Run `python -m app.db.import_pesticide_excel` and `python -m app.db.import_chilli_pdf` from this directory to import source records. These commands are idempotent by source/sheet/row or source/page.
- SQLite startup applies additive columns and creates new tables without deleting existing records.

The chilli PDF is an F1 chilli fertilizer and spraying chart. Its extracted text has damaged spacing and ambiguous table alignment, so product/dose associations and spray combinations need expert transcription and verification before they can become structured active rules. No imported pesticide recommendation is activated.

No tomato YAML or tomato guide, trained CNN model artifact, class labels, preprocessing, or inference service are present in this checkout. The scan screen reports model unavailability and does not produce predictions. Add the reviewed tomato source and a validated model package/training dataset before enabling those capabilities.

## Safety and data integrity
Source schedules are not automatically treated as universal recommendations. Units, area basis,
variety, stage, application method, product label and local applicability must be verified first.
