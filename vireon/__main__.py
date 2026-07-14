"""
VIREON CLI entry point.

Enables:
    vireon run --attack noise
    vireon ui --port 7777
    vireon compile script.rme
    vireon info
"""

import sys
import os
import click
import subprocess
from vireon.core.validation import ValidationRunner

# Ensure the project root is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@click.group()
def cli():
    """VIREON — Virtual Neurosecurity Laboratory"""
    pass


@cli.command()
@click.argument('config_file', required=False)
@click.option('--duration', type=float, default=10.0, help='Simulation duration in seconds')
@click.option('--board', type=click.Choice(['synthetic', 'pieeg', 'cyton', 'ganglion', 'muse', 'emotiv']), default='synthetic')
@click.option('--serial-port', type=str, default='', help='Serial port for physical OpenBCI boards')
@click.option('--dataset', type=str, default=None, help='Path to pre-recorded dataset')
@click.option('--attack', type=str, default='', help='Type of attack to inject')
@click.option('--seed', type=int, default=None, help='Random seed for deterministic reproducibility')
def run(config_file, duration, board, serial_port, dataset, attack, seed):
    """Run a headless simulation experiment."""
    from vireon.core.config import load_config, ExperimentConfig
    from vireon.core.coordinator import Coordinator

    if config_file and os.path.exists(config_file):
        click.echo(f"[VIREON] Loading experiment config: {config_file}")
        config = load_config(config_file)
    else:
        config = ExperimentConfig()
        config.duration_sec = duration
        config.device.type = board
        config.device.serial_port = serial_port
        config.dataset.path = dataset
        if attack:
            config.attacks.active.append(attack)

    if seed is not None:
        config.seed = seed

    coordinator = Coordinator(config)
    coordinator.setup()
    coordinator.run()
    coordinator.teardown()


@cli.command()
@click.option('--port', type=int, default=7777, help='Port to run the Streamlit dashboard on')
@click.option('--host', type=str, default='localhost', help='Host address to bind to (use 0.0.0.0 for Docker)')
def ui(port, host):
    """Launch the interactive Streamlit Web UI."""
    click.echo(f"[VIREON] Launching Dashboard on {host}:{port}...")
    dashboard_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "dashboard", "app.py"))
    
    # Run streamlit as a subprocess
    try:
        subprocess.run(["streamlit", "run", dashboard_path, "--server.port", str(port), "--server.address", host])
    except FileNotFoundError:
        click.secho("Error: Streamlit is not installed. Run `pip install streamlit`.", fg="red")


@cli.command()
def validate():
    """Run the Automated Validation Suite."""
    runner = ValidationRunner()
    runner.run_all()


@cli.command()
@click.argument('source_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output bytecode file')
def compile(source_file, output):
    """Compile a Runemate (.rme) script into secure bytecode."""
    try:
        import vireon_runemate  # type: ignore
    except ImportError:
        click.secho("Error: vireon_runemate extension not found. Did you run `pip install -e .` with maturin?", fg="red")
        return
        
    click.echo(f"[Runemate] Compiling {source_file}...")
    with open(source_file, 'r') as f:
        source_code = f.read()

    try:
        bytecode = vireon_runemate.compile_script(source_code)
        if output:
            with open(output, 'wb') as f:
                f.write(bytes(bytecode))
            click.echo(f"Saved bytecode to {output}")
        else:
            click.echo(f"Compiled successfully. {len(bytecode)} bytes.")
    except Exception as e:
        click.secho(f"Compilation failed: {e}", fg="red")


@cli.command()
def info():
    """Display platform information and registered plugins."""
    from vireon.core.plugin_registry import PluginRegistry, register_builtin_plugins

    click.echo("=" * 60)
    click.echo(" VIREON — Virtual Neurosecurity Laboratory")
    click.echo("=" * 60)
    click.echo(" Version: 0.3.0")
    click.echo(f" Python:  {sys.version.split()[0]}")
    click.echo()

    registry = PluginRegistry()
    register_builtin_plugins(registry)

    for category in sorted(registry.list_categories()):
        plugins = registry.list_category(category)
        click.echo(f" [{category}]")
        for p in plugins:
            click.echo(f"   • {p.name:20s} {p.description}")
        click.echo()

    click.echo("=" * 60)


@cli.command()
@click.option('--output', '-o', type=click.Path(), default='sbom.json', help='Output file path')
def sbom(output):
    """Generate a CycloneDX 1.5 Software Bill of Materials (FDA 524B)."""
    from vireon.core.sbom import generate_sbom, save_sbom, print_sbom_summary

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    bom = generate_sbom(project_root)
    save_sbom(bom, output)
    print_sbom_summary(bom)
    click.echo(f"\n  SBOM saved to: {os.path.abspath(output)}")


@cli.command('compliance-report')
@click.option('--output', '-o', type=click.Path(), default='compliance_report.json', help='Output file path')
def compliance_report(output):
    """Generate an FDA 524B compliance report with gap analysis."""
    from vireon.core.compliance import generate_compliance_report, save_compliance_report, print_compliance_report

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    report = generate_compliance_report(project_root)
    save_compliance_report(report, output)
    print_compliance_report(report)
    click.echo(f"\n  Report saved to: {os.path.abspath(output)}")

@cli.command('audit-spdf')
def audit_spdf():
    """Audit the repository for FDA 524B Secure Product Development Framework (SPDF) compliance."""
    from vireon.core.spdf_auditor import SPDFAuditor
    
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    auditor = SPDFAuditor(project_root)
    results = auditor.audit()
    auditor.print_report(results)

@cli.command('monitor')
def monitor():
    """Run FDA 524B postmarket vulnerability monitoring against the SBOM."""
    from vireon.plugins.reports.vulnerability_monitor import VulnerabilityMonitor
    
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    monitor_app = VulnerabilityMonitor(project_root)
    results = monitor_app.run_scan()
    monitor_app.print_report(results)

@cli.command()
@click.option('--iterations', '-n', type=int, default=1000, help='Number of fuzz test cases')
@click.option('--secure', is_flag=True, default=False, help='Test secure (AES-GCM) mode')
@click.option('--verbose', '-v', is_flag=True, default=False, help='Print details of each test')
@click.option('--protocol', type=click.Choice(['vireon', 'brainflow']), default='vireon', help='Protocol to fuzz')
@click.option('--seed', type=int, default=None, help='Random seed for reproducibility')
@click.option('--output', '-o', type=click.Path(), default=None, help='Save report to JSON file')
def fuzz(iterations, secure, verbose, protocol, seed, output):
    """Run protocol fuzzer against telemetry parser."""
    from vireon.core.fuzzer import ProtocolFuzzer, BrainFlowFuzzer, print_fuzz_report, save_fuzz_report
    
    click.echo(f"Starting fuzzing campaign ({iterations} iterations, protocol={protocol})...")
    if protocol == 'brainflow':
        fuzzer = BrainFlowFuzzer(seed=seed)
    else:
        fuzzer = ProtocolFuzzer(seed=seed)
        
    report = fuzzer.run_campaign(iterations=iterations, secure=secure, verbose=verbose)
    print_fuzz_report(report)

    if output:
        save_fuzz_report(report, output)
        click.echo(f"\n  Report saved to: {os.path.abspath(output)}")


@cli.command()
@click.option('--output', '-o', type=click.Path(), default=None, help='Save JSON model to file')
@click.option('--markdown', '-m', type=click.Path(), default=None, help='Save Markdown report to file')
def stride(output, markdown):
    """Auto-generate a STRIDE threat model for the VIREON platform."""
    from vireon.core.stride import generate_stride_model, print_stride_summary, save_stride_model, render_stride_markdown

    model = generate_stride_model()
    print_stride_summary(model)

    if output:
        save_stride_model(model, output)
        click.echo(f"\n  JSON model saved to: {os.path.abspath(output)}")

    if markdown:
        md_content = render_stride_markdown(model)
        with open(markdown, "w", encoding="utf-8") as f:
            f.write(md_content)
        click.echo(f"  Markdown saved to: {os.path.abspath(markdown)}")


@cli.group()
def ctf():
    """Capture-the-Flag neurosecurity challenges."""
    pass


@ctf.command('list')
def ctf_list():
    """List all available CTF challenges."""
    from vireon.ctf.engine import ChallengeRunner, print_challenge_list
    runner = ChallengeRunner()
    print_challenge_list(runner.list_challenges())


@ctf.command('start')
@click.argument('challenge_id')
def ctf_start(challenge_id):
    """Start a CTF challenge interactively."""
    from vireon.ctf.engine import ChallengeRunner, print_challenge_result

    runner = ChallengeRunner()
    challenge = runner.load_challenge(challenge_id)
    runner.start()

    click.echo(f"\n{'=' * 60}")
    click.echo(f" CTF Challenge: {challenge.title}")
    click.echo(f" Difficulty: {challenge.difficulty} | Time Limit: {challenge.time_limit_sec:.0f}s")
    click.echo(f" Category: {challenge.category} | Max Points: {challenge.max_points}")
    click.echo(f"{'=' * 60}")
    click.echo(f"\n{challenge.description}\n")

    for obj in challenge.objectives:
        click.echo(f"  Objective [{obj.objective_id}]: {obj.description} ({obj.points} pts)")

    click.echo()

    # Interactive answer loop
    for obj in challenge.objectives:
        answer = click.prompt(f"  [{obj.objective_id}] {obj.description}", type=str)
        result = runner.submit_answer(obj.objective_id, answer)
        if result["correct"]:
            click.secho(f"    ✓ {result['feedback']}", fg="green")
        else:
            click.secho(f"    ✗ {result['feedback']}", fg="red")

    final = runner.finish()
    print_challenge_result(final)


@cli.command('simulate-poisoning')
@click.argument('dataset', type=click.Path(exists=True))
@click.argument('target_class', type=int)
@click.option('--ratio', type=float, default=0.1, help='Poisoning ratio')
@click.option('--mode', type=click.Choice(['label', 'backdoor']), default='label', help='Poisoning mode')
def simulate_poisoning(dataset, target_class, ratio, mode):
    """Simulate training-time data poisoning on a dataset."""
    import numpy as np
    from vireon.attacks.poisoning import LabelFlippingPoisoner, CleanLabelBackdoorPoisoner
    
    click.echo(f"[PoisoningSimulator] Loading dataset: {dataset}")
    try:
        data = np.load(dataset)
        x, y = data['x'], data['y']
    except Exception as e:
        click.echo(f"Error loading dataset: {e}. Expecting npz with 'x' and 'y' arrays.")
        return
        
    click.echo(f"[PoisoningSimulator] Initial shape: X={x.shape}, Y={y.shape}")
    
    if mode == 'label':
        poisoner = LabelFlippingPoisoner(poison_ratio=ratio, target_class=target_class)
        desc = "Label Flipping"
    else:
        poisoner = CleanLabelBackdoorPoisoner(poison_ratio=ratio, target_class=target_class)
        desc = "Clean-Label Backdoor"
        
    click.echo(f"[PoisoningSimulator] Executing {desc} attack (ratio={ratio}, target={target_class})...")
    x_poisoned, y_poisoned = poisoner.poison(x, y)
    
    out_path = f"poisoned_{mode}_{dataset.split('/')[-1]}"
    np.savez(out_path, x=x_poisoned, y=y_poisoned)
    click.echo(f"[PoisoningSimulator] Success! Poisoned dataset saved to: {out_path}")


# Alias for main entrypoint
def main():
    cli()


if __name__ == "__main__":
    main()
