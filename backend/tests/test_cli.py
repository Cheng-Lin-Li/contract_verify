"""CLI harness tests (TDD §16 / Foundation Rule h).

Uses Click's ``CliRunner`` so each pipeline stage is exercised through the same
terminal entry points an operator would use, with the FakeProvider active via
the ``LLM_PROVIDER=fake`` environment the test runner sets.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from click.testing import CliRunner

from cli.main import cli

from tests.helpers import CONTRACT, DEAL_DIR, PLAYBOOK_DIR, STDTERMS_DIR, TERM_SHEET


def test_cli_ingest_outputs_json():
    res = CliRunner().invoke(cli, ["ingest", "--file", str(CONTRACT), "--role", "contract"])
    assert res.exit_code == 0, res.output
    assert '"format"' in res.output


def test_cli_extract_lists_requirements():
    res = CliRunner().invoke(cli, ["extract", "--file", str(TERM_SHEET)])
    assert res.exit_code == 0, res.output
    assert "item_id" in res.output


def test_cli_pipeline_writes_reports():
    with tempfile.TemporaryDirectory() as tmp:
        out_html = Path(tmp) / "report.html"
        out_json = Path(tmp) / "report.json"
        res = CliRunner().invoke(cli, [
            "pipeline",
            "--contract", str(CONTRACT),
            "--sources", str(DEAL_DIR),
            "--playbook", str(PLAYBOOK_DIR),
            "--stdterms", str(STDTERMS_DIR),
            "--contract-type", "services",
            "--out", str(out_html),
            "--json-out", str(out_json),
        ])
        assert res.exit_code == 0, res.output
        assert out_html.exists() and out_html.stat().st_size > 0
        data = json.loads(out_json.read_text())
        assert data["coverage_score"] > 0.0
        assert "attorney_queue" in data
