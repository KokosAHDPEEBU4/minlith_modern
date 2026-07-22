"""Allow running with: python -m src [command]"""
from src.cli import main_cli
raise SystemExit(main_cli())
