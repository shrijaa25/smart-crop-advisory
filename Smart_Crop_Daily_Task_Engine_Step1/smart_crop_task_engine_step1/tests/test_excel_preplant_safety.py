
from app.services.excel_knowledge_service import (
    _is_active,
)
from app.services.excel_knowledge_service import (
    get_active_approved_preplant_tasks,
)


def test_active_boolean_values_are_recognized():
    assert _is_active(True)
    assert _is_active("true")
    assert _is_active("yes")
    assert _is_active(1)


def test_inactive_boolean_values_are_rejected():
    assert not _is_active(False)
    assert not _is_active("false")
    assert not _is_active("no")
    assert not _is_active(None)


def test_current_preplant_records_are_not_activated():
    """Current workbook records are unreviewed and inactive."""
    tasks = get_active_approved_preplant_tasks()

    assert tasks == []


def test_preplant_filter_requires_approval_and_activation():
    """Only verified/approved and active records should qualify."""

    def eligible(row):
        status = str(row.get("review_status") or "").strip().lower()
        return (
            status in {"verified", "approved"}
            and _is_active(row.get("is_active"))
        )

    assert eligible({
        "review_status": "approved",
        "is_active": True,
    })

    assert eligible({
        "review_status": "verified",
        "is_active": "yes",
    })

    assert not eligible({
        "review_status": "needs_review",
        "is_active": True,
    })

    assert not eligible({
        "review_status": "approved",
        "is_active": False,
    })
