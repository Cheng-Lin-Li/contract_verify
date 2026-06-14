"""Click CLI -- function-test harness for every pipeline stage (TDD §16).

Each stage is callable from the terminal so functions can be tested without the
UI (Foundation Rule h). The flagship command is ``pipeline``, which runs the
full three-layer verification end-to-end and writes the report.

Examples::

    python -m cli.main ingest   --file samples/contract/contract.txt --role contract
    python -m cli.main playbook  seed --dir samples/playbook
    python -m cli.main stdterms  seed --dir samples/standard_terms
    python -m cli.main pipeline  --contract samples/contract/contract.txt \\
                                 --sources samples/deal \\
                                 --playbook samples/playbook \\
                                 --stdterms samples/standard_terms \\
                                 --out report.html
    python -m cli.main audit     --doc-id <uuid> --format json
"""

from __future__ import annotations

import json
from pathlib import Path

import click

from app.audit.audit_log import AuditLog
from app.config import get_settings
from app.core.enums import DocRole
from app.ingestion.ingest_service import IngestService
from app.llm.factory import get_provider
from app.logging_setup import get_logger
from app.pipeline import VerificationPipeline
from app.references.extractor import RequirementExtractor
from app.references.loaders import load_playbook, load_standard_terms
from app.report.report_builder import render_html

log = get_logger("cli")


@click.group()
def cli() -> None:
    """contract_verify command-line interface."""


@cli.command()
def doctor() -> None:
    """Report the deployment model, per-component data residency, and guardrail warnings.

    Use this to confirm where each component runs before processing real
    contracts -- e.g. that an ``on_prem`` deployment is not silently routing
    documents to a cloud LLM.
    """
    s = get_settings()
    residency = s.component_residency()
    warnings = s.validate_deployment()
    click.echo(f"Deployment mode : {s.deployment_mode}")
    click.echo("Component residency:")
    for component, location in residency.items():
        click.echo(f"  - {component:<9}: {location}")
    if warnings:
        click.echo("\nGuardrail warnings:")
        for w in warnings:
            click.echo(f"  ! {w}")
    else:
        click.echo("\nNo guardrail warnings: placement is consistent with the declared mode.")


@cli.command()
@click.option("--file", "file_path", required=True, type=click.Path(exists=True))
@click.option("--role", type=click.Choice([r.value for r in DocRole]), default="contract")
def ingest(file_path: str, role: str) -> None:
    """Ingest a single document and print its CIR as JSON."""
    doc = IngestService().ingest_file(file_path, DocRole(role))
    click.echo(json.dumps(doc.to_dict(), indent=2, default=str))


@cli.group()
def playbook() -> None:
    """Layer-2 playbook commands."""


@playbook.command("seed")
@click.option("--dir", "directory", required=True, type=click.Path(exists=True))
def playbook_seed(directory: str) -> None:
    """Load and print the Layer-2 playbook reference items."""
    items = load_playbook(directory)
    click.echo(json.dumps([i.to_dict() for i in items], indent=2, default=str))


@cli.group()
def stdterms() -> None:
    """Layer-3 standard-terms commands."""


@stdterms.command("seed")
@click.option("--dir", "directory", required=True, type=click.Path(exists=True))
@click.option("--contract-type", default=None)
def stdterms_seed(directory: str, contract_type: str | None) -> None:
    """Load and print the Layer-3 standard-terms reference items."""
    items = load_standard_terms(directory, contract_type=contract_type)
    click.echo(json.dumps([i.to_dict() for i in items], indent=2, default=str))


@cli.command()
@click.option("--file", "file_path", required=True, type=click.Path(exists=True))
def extract(file_path: str) -> None:
    """Extract Layer-1 requirements from one deal-source document."""
    doc = IngestService().ingest_file(file_path, DocRole.DEAL_SOURCE)
    extractor = RequirementExtractor(get_provider())
    items = extractor.extract(doc)
    click.echo(json.dumps([i.to_dict() for i in items], indent=2, default=str))


@cli.command()
@click.option("--contract", "contract_path", required=True, type=click.Path(exists=True))
@click.option("--sources", "sources_dir", required=True, type=click.Path(exists=True))
@click.option("--playbook", "playbook_dir", required=True, type=click.Path(exists=True))
@click.option("--stdterms", "stdterms_dir", required=True, type=click.Path(exists=True))
@click.option("--contract-type", default=None)
@click.option("--out", "out_path", default=None, help="Write HTML report to this path.")
@click.option("--json-out", "json_path", default=None, help="Write JSON report to this path.")
def pipeline(
    contract_path: str,
    sources_dir: str,
    playbook_dir: str,
    stdterms_dir: str,
    contract_type: str | None,
    out_path: str | None,
    json_path: str | None,
) -> None:
    """Run the full three-layer verification pipeline and emit the report."""
    sources = [str(p) for p in sorted(Path(sources_dir).glob("*")) if p.is_file()]
    result = VerificationPipeline().run(
        contract_path=contract_path,
        deal_source_paths=sources,
        playbook_dir=playbook_dir,
        standard_terms_dir=stdterms_dir,
        contract_type=contract_type,
    )
    report = result.report
    click.echo(
        f"Coverage {report.coverage_score} · Risk {report.risk_score} · "
        f"Auto-confirm: {report.auto_confirm}"
    )
    if report.blocking_reasons:
        click.echo("Blocking reasons:")
        for reason in report.blocking_reasons:
            click.echo(f"  - {reason}")
    if out_path:
        Path(out_path).write_text(render_html(report), encoding="utf-8")
        click.echo(f"HTML report -> {out_path}")
    if json_path:
        Path(json_path).write_text(report.to_json(), encoding="utf-8")
        click.echo(f"JSON report -> {json_path}")
    if not out_path and not json_path:
        click.echo(report.to_json())


@cli.command()
@click.option("--doc-id", "doc_id", required=True)
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json")
def audit(doc_id: str, fmt: str) -> None:
    """Print the audit trail for a contract run."""
    events = AuditLog(get_settings().audit_log_path).events_for(doc_id)
    if fmt == "json":
        click.echo(json.dumps(events, indent=2, default=str))
    else:
        for e in events:
            click.echo(f"{e['occurred_at']} {e['event_type']} {e.get('item_id') or ''} "
                       f"{e.get('status') or ''}")


def main() -> None:
    """Entry point for ``python -m cli.main``."""
    cli()


if __name__ == "__main__":
    main()
