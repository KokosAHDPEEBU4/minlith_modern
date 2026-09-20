"""Repository for CRUD operations on samples and calculations."""

from __future__ import annotations

import logging
import shutil
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.core.models import (
    CalculationResult,
    MineralComposition,
    OxideComposition,
    Sample,
)
from src.database.engine import get_session
from src.database.models import (
    CalculationDB,
    CalculationMineralDB,
    SampleDB,
    SampleOxideDB,
)

logger = logging.getLogger(__name__)

# Oxide fields that map to SampleOxideDB rows
_OXIDE_FIELDS = [
    "sio2", "tio2", "al2o3", "fe2o3", "feo", "mgo", "cao",
    "na2o", "k2o", "p2o5", "mno", "c", "so3", "f", "cl", "s", "co2", "so",
]

# Mineral fields in MineralComposition
_MINERAL_FIELDS = [
    "ab", "an", "or_", "ill", "chl", "kn", "mm", "gb", "q", "dl",
    "ank", "cc", "rch", "sd", "srp", "mst", "ht", "prl",
    "ap", "pr", "hl", "fl", "rt", "gy", "c",
]


class SampleRepository:
    """CRUD for samples in SQLite."""

    def __init__(self, session: Session | None = None) -> None:
        self._session_factory = session or get_session

    def _session(self) -> Session:
        if callable(self._session_factory):
            return self._session_factory()
        return self._session_factory

    @contextmanager
    def _scoped_session(self) -> Iterator[Session]:
        """Session that is always closed after use (returns connection to pool)."""
        session = self._session()
        try:
            yield session
        finally:
            session.close()

    def save_sample(self, sample: Sample) -> int:
        """Save a sample and return its ID."""
        with self._scoped_session() as session:
            try:
                db_sample = SampleDB(name=sample.name)
                session.add(db_sample)
                session.flush()

                for field in _OXIDE_FIELDS:
                    val = getattr(sample.composition, field, 0.0)
                    if val != 0.0:
                        session.add(SampleOxideDB(
                            sample_id=db_sample.id, oxide=field, value=val,
                        ))

                session.commit()
                logger.debug("Saved sample %s (id=%d)", sample.name, db_sample.id)
                return db_sample.id
            except Exception:
                session.rollback()
                raise

    def save_result(self, result: CalculationResult) -> int:
        """Save a calculation result. Creates/updates sample, returns calculation ID."""
        with self._scoped_session() as session:
            try:
                # Find or create sample
                db_sample = session.query(SampleDB).filter_by(name=result.sample_name).first()
                if db_sample is None:
                    db_sample = SampleDB(name=result.sample_name)
                    session.add(db_sample)
                    session.flush()

                    for field in _OXIDE_FIELDS:
                        val = getattr(result.input_composition, field, 0.0)
                        if val != 0.0:
                            session.add(SampleOxideDB(
                                sample_id=db_sample.id, oxide=field, value=val,
                            ))

                # Create calculation
                db_calc = CalculationDB(
                    sample_id=db_sample.id,
                    rock_type=int(result.rock_type),
                    F=result.coefficients.F,
                    A=result.coefficients.A,
                    k1=result.coefficients.k1,
                    k2=result.coefficients.k2,
                    k3=result.coefficients.k3,
                    k4=result.coefficients.k4,
                    warnings="\n".join(result.warnings),
                )
                session.add(db_calc)
                session.flush()

                # Save minerals (formula units)
                for field in _MINERAL_FIELDS:
                    fu_val = getattr(result.minerals_formula, field, 0.0)
                    wt_val = getattr(result.minerals_weight, field, 0.0)
                    if fu_val != 0.0 or wt_val != 0.0:
                        session.add(CalculationMineralDB(
                            calculation_id=db_calc.id,
                            mineral=field,
                            formula_units=fu_val,
                            weight_percent=wt_val,
                        ))

                session.commit()
                logger.debug("Saved calculation id=%d for %s", db_calc.id, result.sample_name)
                return db_calc.id
            except Exception:
                session.rollback()
                raise

    def get_sample(self, sample_id: int) -> Optional[Sample]:
        with self._scoped_session() as session:
            db_sample = session.get(SampleDB, sample_id)
            if db_sample is None:
                return None
            oxide_data = {o.oxide: o.value for o in db_sample.oxides}
            return Sample(
                name=db_sample.name,
                composition=OxideComposition(**{k: oxide_data.get(k, 0.0) for k in _OXIDE_FIELDS}),
            )

    def list_samples(self, limit: int = 100) -> list[tuple[int, str]]:
        with self._scoped_session() as session:
            rows = session.query(SampleDB.id, SampleDB.name).order_by(desc(SampleDB.created_at)).limit(limit).all()
            return [(r.id, r.name) for r in rows]

    def delete_sample(self, sample_id: int) -> None:
        with self._scoped_session() as session:
            db_sample = session.query(SampleDB).filter(SampleDB.id == sample_id).first()
            if db_sample:
                session.delete(db_sample)
                session.commit()

    def get_recent_results(self, limit: int = 50) -> list[dict]:
        """Get recent calculation results with sample names."""
        with self._scoped_session() as session:
            rows = (
                session.query(CalculationDB, SampleDB.name, SampleDB.id)
                .join(SampleDB, CalculationDB.sample_id == SampleDB.id)
                .order_by(desc(CalculationDB.created_at))
                .limit(limit)
                .all()
            )
            results = []
            for calc, name, sample_id in rows:
                minerals = {m.mineral: m.weight_percent for m in calc.minerals}
                results.append({
                    "id": calc.id,
                    "sample_id": sample_id,
                    "sample": name,
                    "rock_type": calc.rock_type,
                    "F": calc.F,
                    "A": calc.A,
                    "minerals": minerals,
                    "created_at": calc.created_at.isoformat() if calc.created_at else "",
                })
            return results

    def search_samples(self, query: str) -> list[tuple[int, str]]:
        with self._scoped_session() as session:
            rows = session.query(SampleDB.id, SampleDB.name).filter(
                SampleDB.name.ilike(f"%{query}%")
            ).limit(50).all()
            return [(r.id, r.name) for r in rows]

    def cleanup_old_records(self, keep_last: int = 100) -> int:
        """Удалить старые записи, оставив последние keep_last."""
        with self._scoped_session() as session:
            try:
                # Get IDs to keep
                keep_ids = (
                    session.query(CalculationDB.id)
                    .order_by(desc(CalculationDB.created_at))
                    .limit(keep_last)
                    .all()
                )
                keep_ids = {r[0] for r in keep_ids}

                # Delete old calculations
                old_calcs = session.query(CalculationDB).filter(
                    ~CalculationDB.id.in_(keep_ids)
                ).all()
                count = len(old_calcs)
                for calc in old_calcs:
                    session.delete(calc)

                session.commit()
                logger.info("Cleaned up %d old calculation records", count)
                return count
            except Exception:
                session.rollback()
                raise

    def get_stats(self) -> dict:
        """Получить статистику БД."""
        with self._scoped_session() as session:
            return {
                "samples": session.query(SampleDB).count(),
                "calculations": session.query(CalculationDB).count(),
            }

    def backup(self, dest_path: Path | str) -> Path:
        """Создать резервную копию БД."""
        from src.database.engine import _DB_PATH as DB_PATH
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.suffix != ".db":
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = dest / f"minlith_backup_{ts}.db"
        shutil.copy2(str(DB_PATH), str(dest))
        logger.info("Backup created: %s", dest)
        return dest

    def export_results_json(self, dest_path: Path | str) -> None:
        """Экспорт всех результатов в JSON."""
        import json
        results = self.get_recent_results(limit=10000)
        with open(dest_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info("Exported %d results to %s", len(results), dest_path)

    def import_results_json(self, src_path: Path | str) -> int:
        """Импорт результатов из JSON. Возвращает количество импортированных."""
        import json
        with open(src_path, encoding="utf-8") as f:
            data = json.load(f)
        count = 0
        for entry in data:
            try:
                if "minerals" in entry and "sample" in entry:
                    from src.core.models import (
                        CalculationResult, OxideComposition, MineralComposition,
                        AdaptiveCoefficients, RockType,
                    )
                    result = CalculationResult(
                        sample_name=entry["sample"],
                        input_composition=OxideComposition(),
                        formula_units=None,
                        coefficients=AdaptiveCoefficients(
                            k1=entry.get("k1", 0), k2=entry.get("k2", 0),
                            k3=entry.get("k3", 0), k4=entry.get("k4", 0),
                            F=entry.get("F", 0), A=entry.get("A", 0),
                        ),
                        rock_type=RockType(entry.get("rock_type", 5)),
                        minerals_formula=None,
                        minerals_weight=MineralComposition(**entry.get("minerals", {})),
                        defect={},
                        warnings=[],
                    )
                    self.save_result(result)
                    count += 1
            except Exception as e:
                logger.warning("Import failed for entry: %s", e)
        logger.info("Imported %d results from %s", count, src_path)
        return count
