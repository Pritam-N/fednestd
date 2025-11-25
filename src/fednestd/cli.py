# src/fednestd/cli.py
from __future__ import annotations

from pathlib import Path

import typer

from .config.loaders import load_config
from .training.tier1_trainer import run_core_update
from .training.aggregation import run_expert_aggregation
from .messaging.topics import bootstrap_topics
from .infra.deployment_profiles import load_profile
from .networking.haproxy_config import render_haproxy_config
from .networking.vpn import render_vpn_peer_config
from .federation.client import run_edge_client
from .federation.server import run_fed_server


app = typer.Typer(no_args_is_help=True, help="fednestd - Federated Nested MoE CLI")
tier1_app = typer.Typer(help="Tier 1 (HPC/Data Center) commands")
tier2_app = typer.Typer(help="Tier 2/3 (Edge client) commands")
messaging_app = typer.Typer(help="Kafka messaging utilities")
infra_app = typer.Typer(help="Infra helpers (HAProxy, VPN, profiles)")

app.add_typer(tier1_app, name="tier1")
app.add_typer(tier2_app, name="tier2")
app.add_typer(messaging_app, name="messaging")
app.add_typer(infra_app, name="infra")


@tier1_app.command("core-update")
def tier1_core_update(
    config: Path = typer.Option(..., "--config", "-c", exists=True, readable=True),
) -> None:
    cfg = load_config(config)
    run_core_update(cfg)


@tier1_app.command("aggregate-experts")
def tier1_aggregate_experts(
    config: Path = typer.Option(..., "--config", "-c", exists=True, readable=True),
) -> None:
    cfg = load_config(config)
    run_expert_aggregation(cfg)


@tier1_app.command("run-fed-server")
def tier1_run_fed_server(
    config: Path = typer.Option(..., "--config", "-c", exists=True, readable=True),
) -> None:
    cfg = load_config(config)
    run_fed_server(cfg)


@tier2_app.command("run-client")
def tier2_run_client(
    config: Path = typer.Option(..., "--config", "-c", exists=True, readable=True),
) -> None:
    cfg = load_config(config)
    run_edge_client(cfg)


@messaging_app.command("bootstrap-topics")
def messaging_bootstrap_topics(
    config: Path = typer.Option(..., "--config", "-c", exists=True, readable=True),
) -> None:
    cfg = load_config(config)
    bootstrap_topics(cfg)


@infra_app.command("generate-haproxy-config")
def infra_generate_haproxy_config(
    profile: str = typer.Option("dev", help="Deployment profile (dev/stage/prod)"),
    output: Path = typer.Option(Path("haproxy.cfg"), "--output", "-o"),
) -> None:
    prof = load_profile(profile)
    rendered = render_haproxy_config(prof)
    output.write_text(rendered)
    typer.echo(f"Written HAProxy config to {output}")


@infra_app.command("generate-vpn-config")
def infra_generate_vpn_config(
    profile: str = typer.Option("edge", help="Deployment profile for edge VPN"),
    output: Path = typer.Option(Path("vpn_peer.conf"), "--output", "-o"),
) -> None:
    prof = load_profile(profile)
    rendered = render_vpn_peer_config(prof)
    output.write_text(rendered)
    typer.echo(f"Written VPN peer config to {output}")


@app.command("init-config")
def init_config(
    target: str = typer.Argument(..., help="tier1|tier2"),
    output: Path = typer.Option(Path("config.yaml"), "--output", "-o"),
) -> None:
    """
    Copy example configs from examples/ into your working directory.
    """
    mapping = {
        "tier1": Path(__file__).parent.parent.parent / "examples" / "minimal_tier1_cluster.yaml",
        "tier2": Path(__file__).parent.parent.parent / "examples" / "minimal_tier2_device.yaml",
    }
    if target not in mapping:
        raise typer.BadParameter("target must be one of: tier1, tier2")

    content = mapping[target].read_text()
    output.write_text(content)
    typer.echo(f"Wrote {target} example config to {output}")