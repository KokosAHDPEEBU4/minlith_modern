"""Tests for cli.py — command-line interface."""

from __future__ import annotations

import subprocess
import sys

import pytest


class TestCli:
    def test_version(self):
        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "--version"],
            capture_output=True, text=True, timeout=10, encoding="utf-8",
        )
        assert result.returncode == 0
        assert "0.6.8" in result.stdout

    def test_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "--help"],
            capture_output=True, text=True, timeout=10, encoding="utf-8",
        )
        assert result.returncode == 0
        output = result.stdout or result.stderr or ""
        assert "MINLITH" in output or "minlith" in output.lower()
