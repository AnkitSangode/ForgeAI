"""Read-only recovery assessment for patch executions.

This service never reclaims leases or repeats external side effects.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

from forgeai.domain.patch_execution import PatchExecution, PatchExecutionStatus
from forgeai.domain.repositories.patch_execution_repository import PatchExecutionRepository


class RecoveryDisposition(str, Enum):
    NO_ACTION = "no_action"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    INVALID_STATE = "invalid_state"


@dataclass(frozen=True)
class RecoveryAssessment:
    execution_id: str
    disposition: RecoveryDisposition
    reason: str
    requires_sandbox_inspection: bool = False


class PatchExecutionRecoveryService:
    def __init__(self, execution_repository: PatchExecutionRepository) -> None:
        self.execution_repository = execution_repository

    def assess_by_id(self, execution_id: str, *, now: datetime | None = None) -> RecoveryAssessment:
        execution = self.execution_repository.get_by_id(UUID(execution_id))
        if execution is None:
            raise LookupError(f"Patch execution not found: {execution_id}")
        return self.assess(execution, now=now)

    @staticmethod
    def assess(execution: PatchExecution, *, now: datetime | None = None) -> RecoveryAssessment:
        current = now or datetime.now(UTC)
        if current.tzinfo is None or current.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        current = current.astimezone(UTC)
        status = execution.status
        execution_id = execution.execution_id

        if status in (PatchExecutionStatus.SUCCEEDED, PatchExecutionStatus.FAILED):
            return RecoveryAssessment(execution_id, RecoveryDisposition.NO_ACTION, "Execution is terminal")

        if status == PatchExecutionStatus.PENDING:
            if execution.claim_token or execution.claimed_at or execution.started_at:
                return RecoveryAssessment(execution_id, RecoveryDisposition.INVALID_STATE, "Pending execution has claim or start metadata")
            return RecoveryAssessment(execution_id, RecoveryDisposition.NO_ACTION, "Execution has not been claimed")

        if status not in (PatchExecutionStatus.CLAIMED, PatchExecutionStatus.RUNNING):
            return RecoveryAssessment(execution_id, RecoveryDisposition.INVALID_STATE, "Unrecognized execution status")

        if not execution.claim_token or not execution.claimed_by or execution.claimed_at is None or execution.lease_expires_at is None:
            return RecoveryAssessment(execution_id, RecoveryDisposition.INVALID_STATE, "Active execution is missing claim metadata")

        claimed_at = execution.claimed_at
        expiry = execution.lease_expires_at
        if any(d.tzinfo is None or d.utcoffset() is None for d in (claimed_at, expiry)):
            return RecoveryAssessment(execution_id, RecoveryDisposition.INVALID_STATE, "Claim timestamps must be timezone-aware")
        if expiry <= claimed_at:
            return RecoveryAssessment(execution_id, RecoveryDisposition.INVALID_STATE, "Lease expires before or at claim time")
        if status == PatchExecutionStatus.RUNNING and execution.started_at is None:
            return RecoveryAssessment(execution_id, RecoveryDisposition.INVALID_STATE, "Running execution has no start time")
        if status == PatchExecutionStatus.CLAIMED and execution.started_at is not None:
            return RecoveryAssessment(execution_id, RecoveryDisposition.INVALID_STATE, "Claimed execution unexpectedly has start time")
        if execution.started_at is not None:
            if execution.started_at.tzinfo is None or execution.started_at.utcoffset() is None:
                return RecoveryAssessment(execution_id, RecoveryDisposition.INVALID_STATE, "Start time must be timezone-aware")
            if execution.started_at < claimed_at:
                return RecoveryAssessment(execution_id, RecoveryDisposition.INVALID_STATE, "Execution started before it was claimed")

        if expiry.astimezone(UTC) <= current:
            return RecoveryAssessment(
                execution_id,
                RecoveryDisposition.RECONCILIATION_REQUIRED,
                "Worker lease expired; liveness, sandbox changes, and test evidence must be inspected before any retry",
                requires_sandbox_inspection=True,
            )
        return RecoveryAssessment(execution_id, RecoveryDisposition.NO_ACTION, "Worker lease is still active")
