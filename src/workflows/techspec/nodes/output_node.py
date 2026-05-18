from ..states.techspec_state import TechspecWorkflowState as WorkflowState
import click
from src.tools.filemanager.filemanager import FileManager
from pathlib import Path

LANG_NEXT_STEPS = {
    "rust": {
        "target_repo": "connector-service/",
        "rulesbook_path": "grace/rulesbook/codegen-rust/.gracerules",
    },
    "python": {
        "target_repo": "connector-service-python/",
        "rulesbook_path": "grace/rulesbook/codegen-python/.gracerules",
    },
}


def _find_target_repo(target_repo_name: str) -> "Path | None":
    """Locate a target service repo by name.

    Probes two canonical layouts:
    1. Sibling: <parent>/grace + <parent>/connector-service[-python]/ (post-Plan-D world)
    2. Parent:  connector-service/grace/  (current canonical per setup.md — grace lives inside connector-service)

    Returns the first matching path that exists, or None.
    """
    target_name = target_repo_name.rstrip("/")
    try:
        grace_dir = Path(__file__).resolve().parents[4]
    except IndexError:
        return None  # non-editable install or unexpected layout

    candidates = [
        grace_dir.parent / target_name,           # sibling
        grace_dir.parent,                          # grace's parent IS the target repo (e.g., connector-service/grace)
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir() and candidate.name == target_name:
            return candidate
    return None


def _print_next_step(target_lang: str, connector: str) -> None:
    """Print a language-aware next-step hint, with a warning when the target repo is missing."""
    config = LANG_NEXT_STEPS.get(target_lang)
    if config is None:
        return

    target_repo = _find_target_repo(config["target_repo"])

    if target_repo is None:
        click.echo(f"\n⚠️  Target repo not found: {config['target_repo']}")
        click.echo(
            f"   Tech spec is generated for --target-lang {target_lang}, but "
            f"{config['target_repo']} was not found as a sibling of grace/ or as grace/'s parent."
        )
        click.echo(f"   Either:")
        click.echo(f"     • Set up {config['target_repo']} as a sibling directory of grace/, OR")
        click.echo(f"     • Re-run with --target-lang <other> if you meant a different target.")
        return

    # Also check the rulesbook exists (I2)
    rulesbook = Path(config["rulesbook_path"])
    rulesbook_abs = (target_repo.parent / rulesbook) if not rulesbook.is_absolute() else rulesbook
    # The rulesbook_path in config is repo-root-relative (e.g., 'grace/rulesbook/codegen-python/.gracerules').
    # If grace lives at target_repo/grace (canonical), rulesbook is at target_repo/grace/rulesbook/...
    # If grace is a sibling of target_repo, rulesbook is at target_repo.parent/grace/rulesbook/...
    # Try both:
    grace_dir = Path(__file__).resolve().parents[4]
    rulesbook_candidates = [
        grace_dir / rulesbook.relative_to("grace") if str(rulesbook).startswith("grace/") else rulesbook,
        target_repo.parent / rulesbook,
    ]
    rulesbook_found = any(p.exists() for p in rulesbook_candidates)
    if not rulesbook_found:
        click.echo(f"\n⚠️  Rulesbook not found: {config['rulesbook_path']}")
        click.echo(
            f"   Target repo {target_repo} exists, but the rulesbook for --target-lang "
            f"{target_lang} has not been authored yet."
        )
        if target_lang == "python":
            click.echo(f"   Plan C (Python service shell) and Plan D (Python pattern pack) must land first.")
        return

    click.echo(f"\nNext step (target language: {target_lang}):")
    click.echo(f"  Open {config['target_repo']} in your AI agent and run:")
    click.echo(f"    integrate {connector or '<Connector>'} using {config['rulesbook_path']}")


def output_node(state: WorkflowState) -> WorkflowState:
    click.echo(f"\nProcessing Complete!")
    try:
        if "urls_file" not in state:
            filemanager = FileManager("links")
            filename = (state["connector_name"] or state["file_name"])+ "_links.txt"
            filemanager.write_file( filename+ "/" + filename + "_links.txt", "\n".join(state["urls"]))
    except Exception as e:
        click.echo(f"Error writing links file: {e}")
    # Display tech spec preview if available
    if "tech_spec" in state and state["tech_spec"]:
        tech_spec = state["tech_spec"]
        click.echo(f"\nPreview of generated specification:")
        preview = tech_spec[:200] + "..." if len(tech_spec) > 100 else tech_spec
        click.echo("============== Tech Spec Preview ==============")
        click.echo(preview)
        click.echo("===============================================")
    
    # Display summary
    click.echo(f"\nSummary:")
    
    metadata = state["metadata"]
    successful_crawls = metadata.get("successful_crawls", 0)
    failed_crawls = metadata.get("failed_crawls", 0)
    
    click.echo(f"• Processed {successful_crawls} documentation source(s)")
    
    if failed_crawls > 0:
        click.echo(f"• Failed to process {failed_crawls} source(s)")
    
    if "tech_spec" in state:
        click.echo(f"• Generated {len(state['tech_spec'])} character specification")
    
    if state.get("enhanced_spec"):
        click.echo(f"• Enhanced specification: {len(state['enhanced_spec'])} characters")
        if state.get("enhanced_spec_filepath"):
            click.echo(f"• Enhanced spec saved to: {state['enhanced_spec_filepath']}")

    if state.get("field_dependency_analysis"):
        click.echo(f"• Field dependency analysis: {len(state['field_dependency_analysis'])} characters")
        if state.get("field_dependency_filepath"):
            click.echo(f"• Analysis saved to: {state['field_dependency_filepath']}")

    if state["metadata"].get("mock_server_generated", False):
        click.echo(f"• Mock server generated successfully")
        if "mock_server_dir" in state:
            click.echo(f"• Mock server directory: {state['mock_server_dir']}")
        if "mock_server_process" in state and state["mock_server_process"]:
            click.echo(f"• Mock server running (PID: {state['mock_server_process'].pid})")
    
    click.echo(f"• Results saved to: {state['output_dir']}")
    

    # Display any errors
    if state["errors"]:
        click.echo(f"\nErrors ({len(state['errors'])}):")
        for error in state["errors"]:
            click.echo(f"   {error}")
    
    # Add performance metrics if available
    if "duration" in metadata:
        click.echo(f"\nProcessing time: {metadata['duration']:.2f} seconds")
    
    if "estimated_tokens" in metadata:
        tokens = metadata["estimated_tokens"]
        click.echo(f"Token usage: ~{tokens.get('estimated_input_tokens', 0)} input + {tokens.get('max_output_tokens', 0)} output")

    # Language-aware next-step hint
    target_lang = state.get("target_lang", "python")
    connector = state.get("connector_name") or state.get("file_name") or ""
    _print_next_step(target_lang, connector)

    return state