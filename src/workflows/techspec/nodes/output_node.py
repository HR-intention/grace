from ..states.techspec_state import TechspecWorkflowState as WorkflowState
import click
from src.tools.filemanager.filemanager import FileManager
from pathlib import Path as _Path

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


def _print_next_step(target_lang: str, connector: str) -> None:
    """Print a language-aware next-step hint, with a warning when the target repo is missing."""
    config = LANG_NEXT_STEPS.get(target_lang)
    if config is None:
        return

    grace_dir = _Path(__file__).resolve().parents[4]  # grace/ root
    target_repo = grace_dir.parent / config["target_repo"]

    if not target_repo.exists():
        click.echo(f"\n⚠️  Target repo not found: {target_repo}")
        click.echo(
            f"   Tech spec is generated for --target-lang {target_lang}, but "
            f"{config['target_repo']} is not present at the expected sibling path."
        )
        click.echo(f"   Either:")
        click.echo(f"     • Set up {config['target_repo']} as a sibling directory of grace/, OR")
        click.echo(f"     • Re-run with --target-lang <other> if you meant a different target.")
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