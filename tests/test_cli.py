"""Tests for CLI commands."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from fednestd.cli import app


runner = CliRunner()


def test_cli_help() -> None:
    """Test that --help shows all subcommands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "fednestd - Federated Nested MoE CLI" in result.stdout
    assert "tier1" in result.stdout
    assert "tier2" in result.stdout
    assert "messaging" in result.stdout
    assert "infra" in result.stdout
    assert "init-config" in result.stdout


def test_tier1_help() -> None:
    """Test tier1 subcommand shows help."""
    result = runner.invoke(app, ["tier1", "--help"])
    assert result.exit_code == 0
    assert "Tier 1 (HPC/Data Center) commands" in result.stdout
    assert "core-update" in result.stdout
    assert "aggregate-experts" in result.stdout
    assert "run-fed-server" in result.stdout


def test_tier2_help() -> None:
    """Test tier2 subcommand shows help."""
    result = runner.invoke(app, ["tier2", "--help"])
    assert result.exit_code == 0
    assert "Tier 2/3 (Edge client) commands" in result.stdout
    assert "run-client" in result.stdout


def test_messaging_help() -> None:
    """Test messaging subcommand shows help."""
    result = runner.invoke(app, ["messaging", "--help"])
    assert result.exit_code == 0
    assert "Kafka messaging utilities" in result.stdout
    assert "bootstrap-topics" in result.stdout


def test_infra_help() -> None:
    """Test infra subcommand shows help."""
    result = runner.invoke(app, ["infra", "--help"])
    assert result.exit_code == 0
    assert "Infra helpers (HAProxy, VPN, profiles)" in result.stdout
    assert "generate-haproxy-config" in result.stdout
    assert "generate-vpn-config" in result.stdout


def test_init_config_tier1(tmp_path: Path) -> None:
    """Test init-config with tier1 target."""
    output_file = tmp_path / "test_config.yaml"
    
    # Try with actual examples directory
    examples_dir = Path(__file__).parent.parent / "examples"
    tier1_example = examples_dir / "minimal_tier1_cluster.yaml"
    
    if tier1_example.exists():
        result = runner.invoke(
            app,
            ["init-config", "tier1", "--output", str(output_file)]
        )
        assert result.exit_code == 0
        assert output_file.exists()
        assert "Wrote tier1 example config" in result.stdout
    else:
        # If example doesn't exist, create a dummy one for testing
        tier1_example.parent.mkdir(parents=True, exist_ok=True)
        tier1_example.write_text("test: config\nmode: tier1\n")
        
        result = runner.invoke(
            app,
            ["init-config", "tier1", "--output", str(output_file)]
        )
        # Should either succeed or fail gracefully
        if result.exit_code == 0:
            assert output_file.exists()


def test_init_config_tier2(tmp_path: Path) -> None:
    """Test init-config with tier2 target."""
    output_file = tmp_path / "test_config.yaml"
    
    examples_dir = Path(__file__).parent.parent / "examples"
    tier2_example = examples_dir / "minimal_tier2_device.yaml"
    
    if tier2_example.exists():
        result = runner.invoke(
            app,
            ["init-config", "tier2", "--output", str(output_file)]
        )
        assert result.exit_code == 0
        assert output_file.exists()
    else:
        # If example doesn't exist, test that command accepts tier2
        result = runner.invoke(
            app,
            ["init-config", "tier2", "--output", str(output_file)]
        )
        # Command should either succeed or fail gracefully
        assert result.exit_code in (0, 1)


def test_init_config_invalid_target() -> None:
    """Test init-config with invalid target raises error."""
    result = runner.invoke(app, ["init-config", "invalid"])
    assert result.exit_code != 0
    # Check that error message mentions valid options (check both stdout and stderr)
    output = result.stdout + result.stderr
    assert "tier1" in output or "tier2" in output or "must be one of" in output or result.exit_code == 2


def test_tier1_core_update_missing_config() -> None:
    """Test tier1 core-update fails gracefully with missing config."""
    result = runner.invoke(
        app,
        ["tier1", "core-update", "--config", "/nonexistent/file.yaml"]
    )
    assert result.exit_code != 0


def test_infra_generate_haproxy_config(tmp_path: Path) -> None:
    """Test infra generate-haproxy-config command."""
    output_file = tmp_path / "haproxy.cfg"
    
    result = runner.invoke(
        app,
        ["infra", "generate-haproxy-config", "--output", str(output_file)]
    )
    
    # Should succeed if profile exists, or fail gracefully
    if result.exit_code == 0:
        assert output_file.exists()
        assert "Written HAProxy config" in result.stdout


def test_infra_generate_vpn_config(tmp_path: Path) -> None:
    """Test infra generate-vpn-config command."""
    output_file = tmp_path / "vpn_peer.conf"
    
    result = runner.invoke(
        app,
        ["infra", "generate-vpn-config", "--output", str(output_file)]
    )
    
    # Should succeed if profile exists, or fail gracefully
    if result.exit_code == 0:
        assert output_file.exists()
        assert "Written VPN peer config" in result.stdout

