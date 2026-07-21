# MINLITH Modern

Normative mineralogical calculation from rock chemical composition.

## Overview

MINLITH Modern is a rewrite of the legacy Excel-based MINLITH program into a modern Python desktop application. It converts oxide weight percentages (SiO₂, TiO₂, Al₂O₃, Fe₂O₃, FeO, MgO, CaO, Na₂O, K₂O, P₂O₅, MnO, C, SO₃, F, Cl, S, CO₂, SO) into mineral weight percentages.

## Features

- Full reproduction of the original MINLITH algorithm (Types 1-5, ~500+ branching conditions)
- PyQt6 GUI with drag-and-drop, preview, progress bars
- SQLite database with versioning
- Built-in charts (bar, pie, QAPF, A-CN-K, A-F-M, TAS)
- Report generator (PDF, Word, HTML)
- Parallel calculation via ProcessPoolExecutor
- Export to Excel, CSV, JSON

## Tech Stack

- Python 3.12+
- PyQt6
- numpy, pandas, openpyxl
- SQLAlchemy + Alembic
- matplotlib + plotly
- reportlab + python-docx + jinja2

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python -m src.gui.app
```

## Building

```bash
python build.py
```
