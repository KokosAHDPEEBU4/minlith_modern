"""ORM models for SQLite database."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Integer, String, Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class SampleDB(Base):
    __tablename__ = "samples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    oxides = relationship("SampleOxideDB", back_populates="sample", cascade="all, delete-orphan")
    calculations = relationship("CalculationDB", back_populates="sample", cascade="all, delete-orphan")


class SampleOxideDB(Base):
    __tablename__ = "sample_oxides"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sample_id = Column(Integer, ForeignKey("samples.id"), nullable=False)
    oxide = Column(String(32), nullable=False)
    value = Column(Float, default=0.0)

    sample = relationship("SampleDB", back_populates="oxides")


class CalculationDB(Base):
    __tablename__ = "calculations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sample_id = Column(Integer, ForeignKey("samples.id"), nullable=False)
    rock_type = Column(Integer)
    F = Column(Float)
    A = Column(Float)
    k1 = Column(Float)
    k2 = Column(Float)
    k3 = Column(Float)
    k4 = Column(Float)
    norm_factor = Column(Float)
    warnings = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    sample = relationship("SampleDB", back_populates="calculations")
    minerals = relationship("CalculationMineralDB", back_populates="calculation", cascade="all, delete-orphan")


class CalculationMineralDB(Base):
    __tablename__ = "calculation_minerals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    calculation_id = Column(Integer, ForeignKey("calculations.id"), nullable=False)
    mineral = Column(String(32), nullable=False)
    formula_units = Column(Float, default=0.0)
    weight_percent = Column(Float, default=0.0)

    calculation = relationship("CalculationDB", back_populates="minerals")


class TagDB(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)


class SampleTagDB(Base):
    __tablename__ = "sample_tags"

    sample_id = Column(Integer, ForeignKey("samples.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)
