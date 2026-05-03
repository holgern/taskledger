"""Command metadata inventory with audience, effect, surface, and phase."""

from __future__ import annotations

from typing import NamedTuple

# ── audience constants ────────────────────────────────────────────────
STABLE_FOR_AGENTS = "stable_for_agents"
BETA_FOR_AGENTS = "beta_for_agents"
HUMAN_ORIENTED = "human_oriented"
REPAIR = "repair"

# ── surface constants ─────────────────────────────────────────────────
PRIMARY = "primary"
SUPPORT = "support"
ADVANCED = "advanced"
HUMAN = "human"
REPAIR_SURFACE = "repair"
MIGRATION = "migration"
BETA = "beta"

# ── phase constants ───────────────────────────────────────────────────
PHASE_SETUP = "setup"
PHASE_PLANNING = "planning"
PHASE_APPROVAL = "approval"
PHASE_IMPLEMENTATION = "implementation"
PHASE_VALIDATION = "validation"
PHASE_REPORTING = "reporting"
PHASE_TRANSFER = "transfer"
PHASE_RELEASE = "release"
PHASE_REPAIR = "repair"
PHASE_SEARCH = "search"


class CommandSpec(NamedTuple):
    audience: str
    effect: str
    surface: str
    phase: str


COMMAND_METADATA: dict[str, CommandSpec] = {
    # ── setup / identity ──────────────────────────────────────────
    "actor whoami": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", PRIMARY, PHASE_SETUP
    ),
    "actor set": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_SETUP
    ),
    "actor clear": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_SETUP
    ),
    "harness set": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_SETUP
    ),
    "harness clear": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_SETUP
    ),
    # ── orientation ───────────────────────────────────────────────
    "init": CommandSpec(STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_SETUP),
    "next-action": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", PRIMARY, PHASE_REPORTING
    ),
    "can": CommandSpec(STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_REPORTING),
    "context": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", PRIMARY, PHASE_REPORTING
    ),
    # ── task management ───────────────────────────────────────────
    "task create": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_PLANNING
    ),
    "task activate": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_PLANNING
    ),
    "task deactivate": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_PLANNING
    ),
    "task follow-up": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_PLANNING
    ),
    "task record": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_PLANNING
    ),
    "task active": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", PRIMARY, PHASE_REPORTING
    ),
    "task show": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", PRIMARY, PHASE_REPORTING
    ),
    "task list": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_REPORTING
    ),
    "task edit": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", ADVANCED, PHASE_PLANNING
    ),
    "task cancel": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", ADVANCED, PHASE_PLANNING
    ),
    "task uncancel": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", ADVANCED, PHASE_PLANNING
    ),
    "task close": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", ADVANCED, PHASE_PLANNING
    ),
    "task events": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", ADVANCED, PHASE_REPORTING
    ),
    # ── planning ──────────────────────────────────────────────────
    "plan start": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_PLANNING
    ),
    "plan template": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", PRIMARY, PHASE_PLANNING
    ),
    "plan guidance": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", PRIMARY, PHASE_PLANNING
    ),
    "plan upsert": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_PLANNING
    ),
    "plan lint": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", PRIMARY, PHASE_PLANNING
    ),
    "plan show": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_PLANNING
    ),
    "plan list": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_PLANNING
    ),
    "plan diff": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_PLANNING
    ),
    "plan draft": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_PLANNING
    ),
    "plan propose": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", ADVANCED, PHASE_PLANNING
    ),
    "plan regenerate": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", ADVANCED, PHASE_PLANNING
    ),
    "plan materialize-todos": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", ADVANCED, PHASE_PLANNING
    ),
    "plan command": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_PLANNING
    ),
    "plan revise": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", ADVANCED, PHASE_PLANNING
    ),
    "plan reject": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", ADVANCED, PHASE_APPROVAL
    ),
    # ── approval ──────────────────────────────────────────────────
    "plan accept": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_APPROVAL
    ),
    "plan approve": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", ADVANCED, PHASE_APPROVAL
    ),
    # ── questions ─────────────────────────────────────────────────
    "question add": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_PLANNING
    ),
    "question add-many": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_PLANNING
    ),
    "question answer": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_PLANNING
    ),
    "question answer-many": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_PLANNING
    ),
    "question status": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", PRIMARY, PHASE_PLANNING
    ),
    "question answers": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", PRIMARY, PHASE_PLANNING
    ),
    "question list": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_PLANNING
    ),
    "question open": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_PLANNING
    ),
    "question dismiss": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_PLANNING
    ),
    # ── implementation ────────────────────────────────────────────
    "implement start": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_IMPLEMENTATION
    ),
    "implement restart": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_IMPLEMENTATION
    ),
    "implement resume": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_IMPLEMENTATION
    ),
    "implement checklist": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", PRIMARY, PHASE_IMPLEMENTATION
    ),
    "implement command": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_IMPLEMENTATION
    ),
    "implement change": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_IMPLEMENTATION
    ),
    "implement scan-changes": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_IMPLEMENTATION
    ),
    "implement finish": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_IMPLEMENTATION
    ),
    "implement show": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_IMPLEMENTATION
    ),
    "implement status": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_IMPLEMENTATION
    ),
    "implement log": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_IMPLEMENTATION
    ),
    "implement deviation": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_IMPLEMENTATION
    ),
    "implement artifact": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_IMPLEMENTATION
    ),
    # ── todos ─────────────────────────────────────────────────────
    "todo add": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_IMPLEMENTATION
    ),
    "todo done": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_IMPLEMENTATION
    ),
    "todo undone": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_IMPLEMENTATION
    ),
    "todo next": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", PRIMARY, PHASE_IMPLEMENTATION
    ),
    "todo status": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", PRIMARY, PHASE_IMPLEMENTATION
    ),
    "todo show": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_IMPLEMENTATION
    ),
    "todo list": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_IMPLEMENTATION
    ),
    # ── validation ────────────────────────────────────────────────
    "validate start": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_VALIDATION
    ),
    "validate status": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", PRIMARY, PHASE_VALIDATION
    ),
    "validate check": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_VALIDATION
    ),
    "validate finish": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_VALIDATION
    ),
    "validate waive": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", ADVANCED, PHASE_VALIDATION
    ),
    "validate show": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_VALIDATION
    ),
    # ── handoffs ──────────────────────────────────────────────────
    "handoff create": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_TRANSFER
    ),
    "handoff claim": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_TRANSFER
    ),
    "handoff close": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", PRIMARY, PHASE_TRANSFER
    ),
    "handoff show": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", PRIMARY, PHASE_TRANSFER
    ),
    "handoff list": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_TRANSFER
    ),
    "handoff cancel": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_TRANSFER
    ),
    "handoff plan-context": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", ADVANCED, PHASE_TRANSFER
    ),
    "handoff implementation-context": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", ADVANCED, PHASE_TRANSFER
    ),
    "handoff validation-context": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", ADVANCED, PHASE_TRANSFER
    ),
    # ── human-oriented reads ──────────────────────────────────────
    "status": CommandSpec(STABLE_FOR_AGENTS, "safe_read_only", HUMAN, PHASE_REPORTING),
    "view": CommandSpec(STABLE_FOR_AGENTS, "safe_read_only", HUMAN, PHASE_REPORTING),
    "tree": CommandSpec(STABLE_FOR_AGENTS, "safe_read_only", HUMAN, PHASE_REPORTING),
    "serve": CommandSpec(HUMAN_ORIENTED, "safe_read_only", HUMAN, PHASE_REPORTING),
    "task dossier": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", HUMAN, PHASE_REPORTING
    ),
    "task report": CommandSpec(
        HUMAN_ORIENTED, "safe_read_only", HUMAN, PHASE_REPORTING
    ),
    "task transcript": CommandSpec(
        HUMAN_ORIENTED, "safe_read_only", HUMAN, PHASE_REPORTING
    ),
    "commands": CommandSpec(HUMAN_ORIENTED, "safe_read_only", HUMAN, PHASE_REPORTING),
    # ── references / metadata ─────────────────────────────────────
    "file add": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_PLANNING
    ),
    "file remove": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_PLANNING
    ),
    "file list": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_REPORTING
    ),
    "link add": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_PLANNING
    ),
    "link remove": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_PLANNING
    ),
    "link list": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_REPORTING
    ),
    "intro create": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_PLANNING
    ),
    "intro link": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_PLANNING
    ),
    "intro list": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_REPORTING
    ),
    "intro show": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_REPORTING
    ),
    "require add": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_PLANNING
    ),
    "require remove": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_PLANNING
    ),
    "require list": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_REPORTING
    ),
    "require waive": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", ADVANCED, PHASE_PLANNING
    ),
    # ── project transfer / ledgers ────────────────────────────────
    "export": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_TRANSFER
    ),
    "import": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_TRANSFER
    ),
    "snapshot": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_TRANSFER
    ),
    "ledger status": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_TRANSFER
    ),
    "ledger list": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", SUPPORT, PHASE_TRANSFER
    ),
    "ledger fork": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", ADVANCED, PHASE_TRANSFER
    ),
    "ledger switch": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", ADVANCED, PHASE_TRANSFER
    ),
    "ledger adopt": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", ADVANCED, PHASE_TRANSFER
    ),
    "ledger doctor": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", ADVANCED, PHASE_TRANSFER
    ),
    # ── release ───────────────────────────────────────────────────
    "release tag": CommandSpec(
        STABLE_FOR_AGENTS, "ledger_mutation", SUPPORT, PHASE_RELEASE
    ),
    "release list": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", HUMAN, PHASE_RELEASE
    ),
    "release show": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", HUMAN, PHASE_RELEASE
    ),
    "release changelog": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", HUMAN, PHASE_RELEASE
    ),
    # ── search ────────────────────────────────────────────────────
    "search": CommandSpec(BETA_FOR_AGENTS, "safe_read_only", BETA, PHASE_SEARCH),
    "grep": CommandSpec(BETA_FOR_AGENTS, "safe_read_only", BETA, PHASE_SEARCH),
    "symbols": CommandSpec(BETA_FOR_AGENTS, "safe_read_only", BETA, PHASE_SEARCH),
    "deps": CommandSpec(BETA_FOR_AGENTS, "safe_read_only", BETA, PHASE_SEARCH),
    # ── repair / doctor ───────────────────────────────────────────
    "doctor": CommandSpec(REPAIR, "safe_read_only", REPAIR_SURFACE, PHASE_REPAIR),
    "doctor locks": CommandSpec(REPAIR, "safe_read_only", REPAIR_SURFACE, PHASE_REPAIR),
    "doctor schema": CommandSpec(
        REPAIR, "safe_read_only", REPAIR_SURFACE, PHASE_REPAIR
    ),
    "doctor indexes": CommandSpec(
        REPAIR, "safe_read_only", REPAIR_SURFACE, PHASE_REPAIR
    ),
    "lock show": CommandSpec(REPAIR, "safe_read_only", REPAIR_SURFACE, PHASE_REPAIR),
    "lock list": CommandSpec(REPAIR, "safe_read_only", REPAIR_SURFACE, PHASE_REPAIR),
    "lock break": CommandSpec(REPAIR, "ledger_mutation", ADVANCED, PHASE_REPAIR),
    "repair lock": CommandSpec(REPAIR, "ledger_mutation", REPAIR_SURFACE, PHASE_REPAIR),
    "repair index": CommandSpec(
        REPAIR, "ledger_mutation", REPAIR_SURFACE, PHASE_REPAIR
    ),
    "repair run": CommandSpec(REPAIR, "ledger_mutation", REPAIR_SURFACE, PHASE_REPAIR),
    "repair task": CommandSpec(REPAIR, "ledger_mutation", REPAIR_SURFACE, PHASE_REPAIR),
    "repair task-dirs": CommandSpec(
        REPAIR, "ledger_mutation", REPAIR_SURFACE, PHASE_REPAIR
    ),
    "repair planning-command-changes": CommandSpec(
        REPAIR, "ledger_mutation", REPAIR_SURFACE, PHASE_REPAIR
    ),
    "migrate status": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", MIGRATION, PHASE_REPAIR
    ),
    "migrate plan": CommandSpec(
        STABLE_FOR_AGENTS, "safe_read_only", MIGRATION, PHASE_REPAIR
    ),
    "migrate apply": CommandSpec(REPAIR, "ledger_mutation", MIGRATION, PHASE_REPAIR),
    "reindex": CommandSpec(REPAIR, "ledger_mutation", REPAIR_SURFACE, PHASE_REPAIR),
}
