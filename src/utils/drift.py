"""
Schema Drift Detection & Simulation — Phase 7

Provides:
- Hash-based schema fingerprinting
- Drift simulation (applies pre-built drift scenarios)
- Drift detection (compares fingerprints)
- DriftReport generation
"""

import copy
import hashlib
import json
import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ─── Data Models ─────────────────────────────────────────────────────────


class FieldChange(BaseModel):
    """A single detected field change."""
    change_type: str = Field(description="rename | add | remove | type_change")
    entity: str
    field_path: str
    old_value: str | None = None
    new_value: str | None = None
    description: str = ""


class DriftReport(BaseModel):
    """Summary of detected schema drift."""
    drift_detected: bool
    total_changes: int
    changes: list[FieldChange]
    affected_mappings: list[str] = Field(
        default_factory=list,
        description="List of Fairshot fields whose mappings are affected"
    )


# ─── Schema Fingerprinting ──────────────────────────────────────────────


def _hash_field(field_def: Any) -> str:
    """Create a deterministic hash of a field definition."""
    serialized = json.dumps(field_def, sort_keys=True, default=str)
    return hashlib.md5(serialized.encode()).hexdigest()[:12]


def compute_fingerprint(schema: dict) -> dict[str, str]:
    """Compute a hash fingerprint for every field in a schema.

    Returns: dict mapping "entity.field_name" → hash string
    """
    fingerprint = {}
    for entity_name, entity_data in schema.get("entities", {}).items():
        fields = entity_data.get("fields", {})
        for field_name, field_def in fields.items():
            key = f"{entity_name}.{field_name}"
            fingerprint[key] = _hash_field(field_def)
    return fingerprint


# ─── Drift Simulation ───────────────────────────────────────────────────


def apply_drift(original_schema: dict, drift_scenario: dict) -> dict:
    """Apply a drift scenario to a schema, returning the modified schema.

    Does NOT modify the original — returns a deep copy with changes applied.
    """
    schema = copy.deepcopy(original_schema)

    for change in drift_scenario.get("changes", []):
        entity_name = change["entity"]
        entity = schema.get("entities", {}).get(entity_name, {})
        fields = entity.get("fields", {})
        samples = entity.get("sample_records", [])

        if change["type"] == "rename":
            old_name = change["old_field"]
            new_name = change["new_field"]
            if old_name in fields:
                fields[new_name] = fields.pop(old_name)
                # Update sample records
                for record in samples:
                    if old_name in record:
                        record[new_name] = record.pop(old_name)

        elif change["type"] == "add":
            field_name = change["field"]
            fields[field_name] = change["field_def"]
            # Add to sample records
            for record in samples:
                record[field_name] = change.get("sample_value")

        elif change["type"] == "type_change":
            field_name = change["field"]
            if field_name in fields:
                fields[field_name]["type"] = change["new_type"]
                if "new_format" in change:
                    fields[field_name]["format"] = change["new_format"]

        elif change["type"] == "remove":
            field_name = change["field"]
            fields.pop(field_name, None)
            for record in samples:
                record.pop(field_name, None)

    return schema


def load_drift_scenario(drift_path: str) -> dict:
    """Load a drift scenario JSON file."""
    with open(drift_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ─── Drift Detection ────────────────────────────────────────────────────


def detect_drift(
    original_fingerprint: dict[str, str],
    new_fingerprint: dict[str, str],
    drift_scenario: dict | None = None,
) -> DriftReport:
    """Compare two schema fingerprints and return a DriftReport.

    If drift_scenario is provided, uses it for richer change descriptions.
    Otherwise, infers changes from fingerprint diff.
    """
    changes: list[FieldChange] = []

    # Fields removed (in original but not in new)
    for key in original_fingerprint:
        if key not in new_fingerprint:
            entity, field = key.split(".", 1)
            changes.append(FieldChange(
                change_type="remove",
                entity=entity,
                field_path=key,
                old_value=field,
                description=f"Field '{field}' was removed from {entity}",
            ))

    # Fields added (in new but not in original)
    for key in new_fingerprint:
        if key not in original_fingerprint:
            entity, field = key.split(".", 1)
            changes.append(FieldChange(
                change_type="add",
                entity=entity,
                field_path=key,
                new_value=field,
                description=f"New field '{field}' added to {entity}",
            ))

    # Fields changed (in both but different hash)
    for key in original_fingerprint:
        if key in new_fingerprint and original_fingerprint[key] != new_fingerprint[key]:
            entity, field = key.split(".", 1)
            changes.append(FieldChange(
                change_type="type_change",
                entity=entity,
                field_path=key,
                old_value=original_fingerprint[key],
                new_value=new_fingerprint[key],
                description=f"Field '{field}' definition changed in {entity}",
            ))

    # Enrich with drift scenario descriptions if available
    if drift_scenario:
        scenario_changes = {
            c.get("old_field", c.get("field", "")): c.get("description", "")
            for c in drift_scenario.get("changes", [])
        }
        for change in changes:
            field_name = change.field_path.split(".")[-1]
            if field_name in scenario_changes:
                change.description = scenario_changes[field_name]

    # Detect renames: a remove + add in the same entity is likely a rename
    removes = [c for c in changes if c.change_type == "remove"]
    adds = [c for c in changes if c.change_type == "add"]
    for rem in removes:
        for add in adds:
            if rem.entity == add.entity:
                # Check if the drift scenario explicitly marks this as a rename
                if drift_scenario:
                    for sc in drift_scenario.get("changes", []):
                        if sc.get("type") == "rename" and sc.get("old_field") == rem.old_value and sc.get("new_field") == add.new_value:
                            rem.change_type = "rename"
                            rem.new_value = add.new_value
                            rem.description = sc.get("description", f"Field renamed: {rem.old_value} → {add.new_value}")
                            changes.remove(add)
                            break

    return DriftReport(
        drift_detected=len(changes) > 0,
        total_changes=len(changes),
        changes=changes,
    )
