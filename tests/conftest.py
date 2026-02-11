"""Shared test fixtures for kernle-devtools."""

import uuid
from datetime import datetime, timezone

import pytest

from kernle.core import Kernle
from kernle.storage import SQLiteStorage
from kernle.storage.base import TrustAssessment


@pytest.fixture
def diag_setup(tmp_path):
    """Create a Kernle instance for diagnostic testing."""
    db_path = tmp_path / "test_diag.db"
    storage = SQLiteStorage(stack_id="test_agent", db_path=db_path)
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    k = Kernle(stack_id="test_agent", storage=storage, checkpoint_dir=checkpoint_dir, strict=False)
    yield k, storage
    storage.close()


@pytest.fixture
def diag_with_trust(diag_setup):
    """Kernle instance with trust seed for operator-initiated tests."""
    k, storage = diag_setup
    assessment = TrustAssessment(
        id=str(uuid.uuid4()),
        stack_id="test_agent",
        entity="stack-owner",
        dimensions={"general": {"score": 0.95}},
        authority=[{"scope": "all"}],
        created_at=datetime.now(timezone.utc),
    )
    storage.save_trust_assessment(assessment)
    return k, storage
