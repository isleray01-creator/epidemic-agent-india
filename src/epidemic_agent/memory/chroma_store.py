from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from ..config import settings

logger = logging.getLogger(__name__)


class ChromaMemoryStore:
    def __init__(self, persist_dir: Path | None = None):
        self.persist_dir = persist_dir or settings.chroma_db_dir
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        self.collection = self.client.get_or_create_collection(
            name="epidemic_india_history",
            metadata={"description": "Epidemic response decisions and outcomes for India"},
        )
        logger.info(f"ChromaDB initialized at {self.persist_dir}")

    def add_decision(
        self,
        decision_id: str,
        day: int,
        state: str,
        situation_summary: str,
        intervention: str,
        params: dict[str, Any],
        predicted_outcome: dict[str, Any],
        actual_outcome: dict[str, Any] | None = None,
        objective_value: float = 0.0,
        confidence: float = 0.0,
    ):
        metadata = {
            "day": day,
            "state": state,
            "intervention": intervention,
            "objective_value": objective_value,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
        }

        document = json.dumps({
            "situation": situation_summary,
            "intervention": intervention,
            "params": params,
            "predicted": predicted_outcome,
            "actual": actual_outcome,
        })

        self.collection.add(
            ids=[decision_id],
            documents=[document],
            metadatas=[metadata],
        )
        logger.debug(f"Added decision {decision_id} to memory")

    def query_similar(
        self,
        situation_summary: str,
        n_results: int = 5,
        state_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        where = {}
        if state_filter:
            where["state"] = state_filter

        results = self.collection.query(
            query_texts=[situation_summary],
            n_results=n_results,
            where=where if where else None,
        )

        return [
            {
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if results.get("distances") else None,
            }
            for i in range(len(results["ids"][0]))
        ]

    def get_recent_decisions(self, days: int = 30, limit: int = 20) -> list[dict[str, Any]]:
        results = self.collection.get(
            limit=limit,
            where={"day": {"$gte": days}},
        )
        return [
            {"id": results["ids"][i], "document": results["documents"][i], "metadata": results["metadatas"][i]}
            for i in range(len(results["ids"]))
        ]

    def update_outcome(self, decision_id: str, actual_outcome: dict[str, Any]):
        existing = self.collection.get(ids=[decision_id])
        if not existing["ids"]:
            return

        doc = json.loads(existing["documents"][0])
        doc["actual"] = actual_outcome
        self.collection.update(
            ids=[decision_id],
            documents=[json.dumps(doc)],
        )

    def clear(self):
        self.client.delete_collection("epidemic_india_history")
        self.collection = self.client.create_collection(
            name="epidemic_india_history",
            metadata={"description": "Epidemic response decisions and outcomes for India"},
        )


_memory_store: ChromaMemoryStore | None = None


def get_memory_store() -> ChromaMemoryStore:
    global _memory_store
    if _memory_store is None:
        _memory_store = ChromaMemoryStore()
    return _memory_store
