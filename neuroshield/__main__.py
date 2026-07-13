"""
NeuroShield CLI entry point.

Enables:
    neuroshield run --attack noise
    neuroshield ui --port 7777
    neuroshield compile script.rme
    neuroshield info
"""

import sys
import os
import click
import subprocess

# Ensure the project root is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@click.group()
def cli():
    """NeuroShield — Virtual Neurosecurity Laboratory"""
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
    from neuroshield.core.config import load_config, ExperimentConfig
    from neuroshield.core.coordinator import Coordinator

    if config_file and os.path.exists(config_file):
        click.echo(f"[NeuroShield] Loading experiment config: {config_file}")
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
    click.echo(f"[NeuroShield] Launching Dashboard on {host}:{port}...")
    dashboard_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "dashboard", "app.py"))
    
    # Run streamlit as a subprocess
    try:
        subprocess.run(["streamlit", "run", dashboard_path, "--server.port", str(port), "--server.address", host])
    except FileNotFoundError:
        click.secho("Error: Streamlit is not installed. Run `pip install streamlit`.", fg="red")


@cli.command()
@click.argument('source_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output bytecode file')
def compile(source_file, output):
    """Compile a Runemate (.rme) script into secure bytecode."""
    try:
        import neuroshield_runemate  # type: ignore
    except ImportError:
        click.secho("Error: neuroshield_runemate extension not found. Did you run `pip install -e .` with maturin?", fg="red")
        return
        
    click.echo(f"[Runemate] Compiling {source_file}...")
    with open(source_file, 'r') as f:
        source_code = f.read()

    try:
        bytecode = neuroshield_runemate.compile_script(source_code)
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
    from neuroshield.core.plugin_registry import PluginRegistry, register_builtin_plugins

    click.echo("=" * 60)
    click.echo(" NeuroShield — Virtual Neurosecurity Laboratory")
    click.echo("=" * 60)
    click.echo(f" Version: 0.3.0")
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


if __name__ == "__main__":
    cli()
