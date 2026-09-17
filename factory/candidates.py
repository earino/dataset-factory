from pathlib import Path

from .common import FactoryError, identifier, read_json, utcnow, write_json


def create(root, candidate_id):
    identifier(candidate_id)
    folder = Path(root) / "candidates" / candidate_id
    if folder.exists():
        raise FactoryError("Candidate already exists")
    folder.mkdir(parents=True)
    record = {
        "id": candidate_id, "status": "investigating", "created_at": utcnow().isoformat(),
        "domain": None, "prediction_question": None, "prediction_time": None,
        "target_definition": None, "sources": [], "license_evidence": [],
        "construction_script": None, "split_strategy": None,
        "measurements": {}, "jobs": [], "artifacts": [],
        "rejection_reason": None, "review": None, "next_action": "Investigate source and observable target",
    }
    write_json(folder / "record.json", record)
    (folder / "notes.md").write_text(f"# {candidate_id}\n\nRecord dated evidence, decisions, and failed approaches here.\n")
    return record


def listing(root):
    return [read_json(p) for p in sorted((Path(root) / "candidates").glob("*/record.json"))]
