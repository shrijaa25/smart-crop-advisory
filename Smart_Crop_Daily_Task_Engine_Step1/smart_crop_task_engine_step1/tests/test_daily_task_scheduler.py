from datetime import date, datetime, timezone
import multiprocessing
from pathlib import Path
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.main import app
import app.main as main_module
from app.models import CropCycle, DailyTask, Farm, Farmer
from app.services import daily_task_scheduler as scheduler

RUN_DATE = date(2026, 10, 15)


def _acquire_lock_in_child(path: str, ready, release, result_queue):
    lock = scheduler._ProcessLock(Path(path))
    acquired = lock.acquire()
    result_queue.put(acquired)
    ready.set()
    if acquired:
        release.wait(10)
        lock.release()


def setup_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def add_cycle(db: Session, name: str, *, status: str = "active", planting_date=RUN_DATE):
    farmer = Farmer(full_name=name)
    db.add(farmer)
    db.flush()
    farm = Farm(farmer_id=farmer.id, name=f"{name}'s farm")
    db.add(farm)
    db.flush()
    cycle = CropCycle(
        farm_id=farm.id,
        crop_name="tomato",
        planting_date=planting_date,
        status=status,
    )
    db.add(cycle)
    db.flush()
    return cycle


def test_job_generates_across_farmers_idempotently_and_preserves_completed_tasks():
    engine, factory = setup_database()
    try:
        with factory() as db:
            first = add_cycle(db, "Farmer One")
            second = add_cycle(db, "Farmer Two")
            inactive = add_cycle(db, "Inactive", status="inactive")
            future = add_cycle(db, "Future planting", planting_date=date(2026, 10, 16))
            db.commit()
            cycle_ids = (first.id, second.id, inactive.id, future.id)

        first_run = scheduler.run_daily_task_job(RUN_DATE, session_factory=factory)
        assert first_run == {
            "run_date": "2026-10-15",
            "crop_cycles_processed": 2,
            "tasks_created": 2,
            "preplant_tasks_created": 2,
            "errors": 0,
        }
        with factory() as db:
            daily_tasks = db.scalars(
                select(DailyTask)
                .where(DailyTask.source_rule_type == "daily_monitoring")
                .order_by(DailyTask.crop_cycle_id)
            ).all()
            preplant_tasks = db.scalars(
                select(DailyTask).where(
                    DailyTask.source_rule_type == "preplant_checklist"
                )
            ).all()
            assert [task.crop_cycle_id for task in daily_tasks] == list(cycle_ids[:2])
            assert len(preplant_tasks) == 2
            daily_tasks[0].status = "completed"
            db.commit()

        repeated = scheduler.run_daily_task_job(RUN_DATE, session_factory=factory)
        assert repeated["crop_cycles_processed"] == 2
        assert repeated["tasks_created"] == 0
        assert repeated["preplant_tasks_created"] == 0
        with factory() as db:
            daily_tasks = db.scalars(
                select(DailyTask)
                .where(DailyTask.source_rule_type == "daily_monitoring")
                .order_by(DailyTask.crop_cycle_id)
            ).all()
            assert len(daily_tasks) == 2
            assert daily_tasks[0].status == "completed"
    finally:
        engine.dispose()


def test_job_continues_after_one_crop_cycle_fails(monkeypatch):
    engine, factory = setup_database()
    original = scheduler.generate_daily_monitoring_tasks
    try:
        with factory() as db:
            failing = add_cycle(db, "Fails first")
            succeeding = add_cycle(db, "Succeeds second")
            db.commit()
            failing_id, succeeding_id = failing.id, succeeding.id

        def fail_first(db, target_date, crop_cycle_id):
            if crop_cycle_id == failing_id:
                raise RuntimeError("simulated cycle failure")
            return original(db, target_date=target_date, crop_cycle_id=crop_cycle_id)

        monkeypatch.setattr(scheduler, "generate_daily_monitoring_tasks", fail_first)
        result = scheduler.run_daily_task_job(RUN_DATE, session_factory=factory)
        assert result["crop_cycles_processed"] == 2
        assert result["tasks_created"] == 1
        assert result["errors"] == 1
        with factory() as db:
            task_cycle_ids = db.scalars(select(DailyTask.crop_cycle_id)).all()
            assert task_cycle_ids == [succeeding_id]
    finally:
        engine.dispose()


def test_scheduled_date_uses_asia_kolkata(monkeypatch):
    class FixedDateTime:
        @classmethod
        def now(cls, tz):
            assert str(tz) == "Asia/Kolkata"
            return datetime(2026, 10, 14, 19, 0, tzinfo=timezone.utc).astimezone(tz)

    monkeypatch.setattr(scheduler, "datetime", FixedDateTime)
    assert scheduler.india_today() == date(2026, 10, 15)


def test_application_lifespan_starts_and_stops_scheduler(monkeypatch):
    events = []
    monkeypatch.setattr(main_module, "start_daily_task_scheduler", lambda: events.append("start"))
    monkeypatch.setattr(main_module, "stop_daily_task_scheduler", lambda: events.append("stop"))
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200
        assert events == ["start"]
    assert events == ["start", "stop"]


def test_scheduler_starts_once_and_releases_worker_lock(monkeypatch, tmp_path):
    monkeypatch.setattr(scheduler, "_lock_path", lambda: tmp_path / "scheduler.lock")
    assert scheduler.start_daily_task_scheduler() is True
    instance = scheduler._scheduler
    assert instance is not None and instance.running
    job = instance.get_job("daily_crop_monitoring_tasks")
    assert job is not None
    assert job.trigger.timezone == scheduler.INDIA_TZ
    assert str(job.trigger) == "cron[hour='6', minute='0']"
    assert scheduler.start_daily_task_scheduler() is True
    assert scheduler._scheduler is instance
    scheduler.stop_daily_task_scheduler()
    assert scheduler._scheduler is None
    assert scheduler._process_lock is None

    # Shutdown releases the OS lock so a subsequent app process can own it.
    assert scheduler.start_daily_task_scheduler() is True
    scheduler.stop_daily_task_scheduler()


def test_application_lifespan_owns_and_releases_real_scheduler(monkeypatch, tmp_path):
    monkeypatch.setattr(scheduler, "_lock_path", lambda: tmp_path / "lifespan.lock")
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200
        assert scheduler._scheduler is not None
        assert scheduler._scheduler.running
        assert scheduler._process_lock is not None
    assert scheduler._scheduler is None
    assert scheduler._process_lock is None


def test_scheduler_os_lock_excludes_another_worker_process(tmp_path):
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    release = context.Event()
    result_queue = context.Queue()
    path = tmp_path / "shared-scheduler.lock"
    process = context.Process(
        target=_acquire_lock_in_child,
        args=(str(path), ready, release, result_queue),
    )
    process.start()
    try:
        assert ready.wait(10)
        assert result_queue.get(timeout=2) is True
        contender = scheduler._ProcessLock(path)
        assert contender.acquire() is False
        release.set()
        process.join(timeout=10)
        assert process.exitcode == 0
        assert contender.acquire() is True
        contender.release()
    finally:
        release.set()
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)


def test_scheduler_setup_failure_releases_process_lock(monkeypatch, tmp_path):
    path = tmp_path / "setup-failure.lock"

    class BrokenScheduler:
        running = False
        def __init__(self, **kwargs):
            pass
        def add_job(self, *args, **kwargs):
            raise RuntimeError("simulated scheduler setup failure")

    monkeypatch.setattr(scheduler, "_lock_path", lambda: path)
    monkeypatch.setattr(scheduler, "BackgroundScheduler", BrokenScheduler)
    with pytest.raises(RuntimeError, match="setup failure"):
        scheduler.start_daily_task_scheduler()
    assert scheduler._process_lock is None
    contender = scheduler._ProcessLock(path)
    assert contender.acquire() is True
    contender.release()


def test_shutdown_failure_still_releases_process_lock(monkeypatch):
    events = []

    class BrokenScheduler:
        running = True
        def shutdown(self, wait):
            raise RuntimeError("simulated shutdown failure")

    class Lock:
        def release(self):
            events.append("released")

    monkeypatch.setattr(scheduler, "_scheduler", BrokenScheduler())
    monkeypatch.setattr(scheduler, "_process_lock", Lock())
    with pytest.raises(RuntimeError, match="shutdown failure"):
        scheduler.stop_daily_task_scheduler()
    assert scheduler._scheduler is None
    assert scheduler._process_lock is None
    assert events == ["released"]
