"""Daily crop monitoring task generation and scheduler lifecycle."""

from datetime import date, datetime
import hashlib
import logging
import os
from pathlib import Path
import tempfile
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import CropCycle, Farm
from app.services.task_engine import (
    generate_daily_monitoring_tasks,
    generate_daily_tasks,
    generate_irrigation_tasks,
    generate_one_time_fertilizer_tasks,
    generate_stage_milestone_tasks,
    generate_fallback_irrigation_tasks,
)
from app.services.preplant_checklist import generate_preplant_checklist_tasks

logger = logging.getLogger(__name__)
INDIA_TZ = ZoneInfo("Asia/Kolkata")


def india_today() -> date:
    """Return today's date in the scheduler's configured timezone."""
    return datetime.now(INDIA_TZ).date()


def run_daily_task_job(
    target_date: date | None = None,
    *,
    session_factory: sessionmaker[Session] | None = None,
) -> dict[str, int | str]:
    """Generate daily monitoring tasks for all eligible crop cycles."""
    run_date = target_date or india_today()
    factory = session_factory or SessionLocal
    db: Session | None = None
    processed = 0
    created = 0
    preplant_created = 0
    errors = 0

    try:
        db = factory()

        # Generate due pre-planting checklist tasks for future crop cycles.
        try:
            preplant_created += generate_preplant_checklist_tasks(
                db,
                target_date=run_date,
            )
        except Exception:
            errors += 1
            logger.exception(
                "Failed to generate pre-planting checklist tasks"
            )
            db.rollback()

        # Existing daily monitoring logic remains unchanged.

        cycle_ids = db.scalars(
            select(CropCycle.id)
            .where(
                CropCycle.status == "active",
                CropCycle.planting_date <= run_date,
            )
            .order_by(CropCycle.id)
        ).all()

        for cycle_id in cycle_ids:
            processed += 1

            try:
                created += generate_daily_monitoring_tasks(
                    db,
                    target_date=run_date,
                    crop_cycle_id=cycle_id,
                )
            except Exception:
                errors += 1
                logger.exception(
                    "Failed to generate daily task for crop cycle %s",
                    cycle_id,
                )
                db.rollback()

        return {
            "run_date": run_date.isoformat(),
            "crop_cycles_processed": processed,
            "tasks_created": created,
            "preplant_tasks_created": preplant_created,
            "errors": errors,
        }

    finally:
        if db is not None:
            db.close()

class _ProcessLock:
    """Non-blocking OS lock held for the lifetime of the scheduler owner."""

    def __init__(self, path: Path):
        self.path = path
        self._file = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._file = self.path.open("a+b")
            self._file.seek(0)
            if self._file.read(1) == b"":
                self._file.write(b"0")
                self._file.flush()
            self._file.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except (OSError, BlockingIOError):
            if self._file is not None:
                self._file.close()
            self._file = None
            return False

    def release(self) -> None:
        if self._file is None:
            return
        try:
            self._file.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        finally:
            self._file.close()
            self._file = None


def _lock_path() -> Path:
    key = hashlib.sha256(settings.database_url.encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f"smart-crop-daily-scheduler-{key}.lock"


_scheduler: BackgroundScheduler | None = None
_process_lock: _ProcessLock | None = None


def start_daily_task_scheduler() -> bool:
    """Start the 06:00 India-time scheduler if this process owns the lock."""
    global _scheduler, _process_lock
    if _scheduler is not None and _scheduler.running:
        return True

    lock = _ProcessLock(_lock_path())
    if not lock.acquire():
        logger.info("Daily task scheduler not started: another worker owns the scheduler lock")
        return False

    scheduler: BackgroundScheduler | None = None
    try:
        scheduler = BackgroundScheduler(timezone=INDIA_TZ)
        scheduler.add_job(
            run_daily_task_job,
            trigger=CronTrigger(hour=6, minute=0, timezone=INDIA_TZ),
            id="daily_crop_monitoring_tasks",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=3600,
        )
        scheduler.start()
    except Exception:
        try:
            if scheduler is not None and scheduler.running:
                scheduler.shutdown(wait=False)
        finally:
            lock.release()
        raise
    assert scheduler is not None
    _scheduler = scheduler
    _process_lock = lock
    logger.info("Daily task scheduler started; next run is scheduled for 06:00 Asia/Kolkata")
    return True


def stop_daily_task_scheduler() -> None:
    """Stop this process's scheduler and release its worker lock."""
    global _scheduler, _process_lock
    try:
        if _scheduler is not None and _scheduler.running:
            _scheduler.shutdown(wait=True)
    finally:
        _scheduler = None
        if _process_lock is not None:
            _process_lock.release()
            _process_lock = None
        logger.info("Daily task scheduler stopped")
