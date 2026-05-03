from __future__ import annotations

import hashlib
import json

from taskledger.domain.models import PlanRecord


def approved_plan_content_hash(plan: PlanRecord) -> str:
    payload = {
        "body": plan.body,
        "goal": plan.goal,
        "files": list(plan.files),
        "test_commands": list(plan.test_commands),
        "expected_outputs": list(plan.expected_outputs),
        "criteria": [item.to_dict() for item in plan.criteria],
        "todos": [item.to_dict() for item in plan.todos],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = ["approved_plan_content_hash"]
