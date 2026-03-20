from __future__ import annotations

import copy
from dataclasses import dataclass


@dataclass
class Snapshot:
    snapshot_id: str
    branch: str
    description: str
    step: str | None
    state: list[dict]


class MockMemoria:
    """A local in-memory stand-in for Memoria's branch/snapshot workflow."""

    def __init__(self) -> None:
        self.branches: dict[str, list[dict]] = {"main": []}
        self.current_branch = "main"
        self.snapshots: list[Snapshot] = []
        self.snapshot_counter = 0

    def checkout(self, name: str) -> dict:
        if name not in self.branches:
            raise KeyError(f"Unknown branch: {name}")
        self.current_branch = name
        return {"branch": name}

    def create_branch(self, name: str, description: str = "") -> dict:
        parent_state = copy.deepcopy(self.branches[self.current_branch])
        self.branches[name] = parent_state
        if description:
            self.branches[name].append(
                {
                    "type": "branch_created",
                    "branch": name,
                    "parent_branch": self.current_branch,
                    "description": description,
                }
            )
        return {"name": name, "parent": self.current_branch}

    def store(self, content: dict, metadata: dict | None = None) -> dict:
        record = {
            "content": copy.deepcopy(content),
            "metadata": copy.deepcopy(metadata or {}),
        }
        self.branches[self.current_branch].append(record)
        return record

    def retrieve(self, query: str, limit: int = 5) -> list[dict]:
        tokens = [token.lower() for token in query.split() if token.strip()]
        hits: list[dict] = []
        for record in reversed(self.branches[self.current_branch]):
            haystack = f"{record.get('content')} {record.get('metadata')}".lower()
            if not tokens or any(token in haystack for token in tokens):
                hits.append(copy.deepcopy(record))
            if len(hits) >= limit:
                break
        return hits

    def snapshot(self, description: str = "", step: str | None = None) -> dict:
        self.snapshot_counter += 1
        snapshot = Snapshot(
            snapshot_id=f"snap-{self.snapshot_counter:03d}",
            branch=self.current_branch,
            description=description,
            step=step,
            state=copy.deepcopy(self.branches[self.current_branch]),
        )
        self.snapshots.append(snapshot)
        return {
            "snapshot_id": snapshot.snapshot_id,
            "branch": snapshot.branch,
            "description": snapshot.description,
            "step": snapshot.step,
        }

    def list_snapshots(self) -> list[dict]:
        return [
            {
                "snapshot_id": snapshot.snapshot_id,
                "branch": snapshot.branch,
                "description": snapshot.description,
                "step": snapshot.step,
            }
            for snapshot in self.snapshots
        ]

    def rollback(self, snapshot_id: str) -> dict:
        snapshot = self._get_snapshot(snapshot_id)
        self.branches[snapshot.branch] = copy.deepcopy(snapshot.state)
        self.current_branch = snapshot.branch
        return {"snapshot_id": snapshot_id, "branch": snapshot.branch}

    def snapshot_diff(self, snapshot_id: str) -> dict:
        snapshot = self._get_snapshot(snapshot_id)
        current = self.branches[snapshot.branch]
        return {
            "before_count": len(snapshot.state),
            "after_count": len(current),
            "before_last_types": [item.get("content", {}).get("type") for item in snapshot.state[-5:]],
            "after_last_types": [item.get("content", {}).get("type") for item in current[-5:]],
        }

    def diff(self, source: str, target: str) -> dict:
        source_records = self.branches.get(source, [])
        target_records = self.branches.get(target, [])
        return {
            "source": source,
            "target": target,
            "source_count": len(source_records),
            "target_count": len(target_records),
            "source_last_types": [item.get("content", {}).get("type") for item in source_records[-5:]],
            "target_last_types": [item.get("content", {}).get("type") for item in target_records[-5:]],
        }

    def merge(self, source: str, target: str, strategy: str = "ours") -> dict:
        self.branches.setdefault(target, [])
        self.branches[target].append(
            {
                "content": {
                    "type": "merge_marker",
                    "source": source,
                    "target": target,
                    "strategy": strategy,
                },
                "metadata": {"type": "merge"},
            }
        )
        return {"source": source, "target": target, "strategy": strategy}

    def _get_snapshot(self, snapshot_id: str) -> Snapshot:
        for snapshot in self.snapshots:
            if snapshot.snapshot_id == snapshot_id:
                return snapshot
        raise KeyError(f"Unknown snapshot: {snapshot_id}")
