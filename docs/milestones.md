# FedNest Development Milestones

This document outlines the development roadmap for FedNest, organized into clear milestones with goals, key tasks, and acceptance criteria. No dates are specified; map these to your own timeline based on bandwidth.

---

## Milestone 0 – Repo Hygiene & Baseline

**Goal:** Get the scaffolded project into a clean, buildable, testable state.

### Key Tasks

- [ ] Fix `pyproject.toml` (name, deps, console_script `fednestd`)
- [ ] Ensure `src/fednestd/__main__.py` + `cli.py` are wired correctly
- [ ] Implement basic functions (as stubs are done):
  - [ ] `get_logger`
  - [ ] `load_config`
  - [ ] `load_profile`
  - [ ] `render_haproxy_config`
  - [ ] `render_vpn_peer_config`
  - [ ] `get_admin_client`
  - [ ] `bootstrap_topics`
- [ ] Make sure pytest runs and existing tests (`tests/test_cli.py`, etc.) pass or are updated to reflect new CLI
- [ ] Set up basic CI (GitHub Actions) to run:
  - [ ] `pip install -e .`
  - [ ] `pytest`
  - [ ] `pyright` / `mypy` if you want strict typing

### Acceptance Criteria

- [ ] `pip install -e .` works
- [ ] `fednestd --help` works and shows subcommands
- [ ] `pytest` passes
- [ ] Type checker is clean (or only has intentional, documented ignores)

---

## Milestone 1 – Config & CLI Foundation

**Goal:** Make CLI + config handling solid and ergonomic for all main flows.

### Key Tasks

- [ ] Implement `config.models` using Pydantic:
  - [ ] `Tier1Config`
  - [ ] `Tier2Config`
  - [ ] `MessagingConfig`
  - [ ] `InfraConfig`
- [ ] Update `config.loaders.load_config()` to:
  - [ ] Load YAML/JSON
  - [ ] Validate against the correct Pydantic model based on `mode` or `kind` field
- [ ] Wire CLI commands to typed configs:
  - [ ] `fednestd tier1 core-update`
  - [ ] `fednestd tier1 aggregate-experts`
  - [ ] `fednestd tier1 run-fed-server`
  - [ ] `fednestd tier2 run-client`
  - [ ] `fednestd messaging bootstrap-topics`
  - [ ] `fednestd infra generate-haproxy-config`
  - [ ] `fednestd infra generate-vpn-config`
  - [ ] `fednestd init-config ...`
- [ ] Document CLI usage in `docs/cli.md`

### Acceptance Criteria

- [ ] You can generate sample configs with `init-config`
- [ ] Running each CLI command with sample configs logs and exits cleanly (even if training is stubbed)
- [ ] Docs in `docs/cli.md` match the actual command names/flags

---

## Milestone 2 – Core Model & Local Training (No Federation Yet)

**Goal:** Have a working MoE model + adapters and a simple local-only training loop for Tier 1.

### Key Tasks

- [ ] In `model/`:
  - [ ] Implement `moe_model.py` with:
    - [ ] `W_core` (embeddings + attention + norms)
    - [ ] `W_experts` (expert FFN blocks)
  - [ ] Implement `adapters.py` (LoRA/QLoRA layers) for experts
  - [ ] Implement `checkpointing.py` for:
    - [ ] Saving/loading checkpoints
    - [ ] Explicitly separating core, experts, adapters
  - [ ] Implement `quantization.py` basics (e.g. hooks for QLoRA later)
- [ ] In `training/tier1_trainer.py`:
  - [ ] Implement a single-node (non-DeepSpeed) training loop using dummy or small real data
  - [ ] Log metrics (loss) to console or MLflow

### Acceptance Criteria

- [ ] A small sample script / CLI call (e.g. `fednestd tier1 core-update --config examples/minimal_tier1_cluster.yaml`) actually trains for a few steps and writes a checkpoint
- [ ] `tests/test_moe_model.py` and `tests/test_aggregation.py` updated and passing for the new model semantics

---

## Milestone 3 – Tier 1 Distributed Training & Metadata Integration

**Goal:** Move Tier 1 training to real distributed mode and wire in global metadata/governance skeleton.

### Key Tasks

- [ ] Integrate DeepSpeed with `tier1_trainer.py`:
  - [ ] ZeRO optimization
  - [ ] MoE expert parallelism across GPUs
- [ ] Implement basic MLflow integration in Tier1:
  - [ ] Track runs (params, metrics, artifacts)
  - [ ] Save checkpoints as MLflow artifacts
- [ ] Implement minimal hooks for:
  - [ ] `governance/global_ranger.py` – stub calls to check data access policy
  - [ ] `governance/global_metadata.py` – stub integration with DataHub (even if just logging for now)

### Acceptance Criteria

- [ ] Running Tier 1 training in a multi-GPU environment via CLI works (even if using synthetic data)
- [ ] MLflow contains runs and artifacts for those jobs
- [ ] Logs clearly show Ranger/DataHub hooks being invoked (even in stub form)

---

## Milestone 4 – Messaging & Infra Wiring

**Goal:** Get Kafka, HAProxy, and VPN config flows working end-to-end (even if infra is only local/dev).

### Key Tasks

- [ ] Solidify `messaging/kafka_client.py` and `messaging/topics.py`:
  - [ ] `bootstrap_topics` tested against local Kafka (docker-compose or k8s)
- [ ] Implement minimal `scripts/dev_start_cluster.sh` to:
  - [ ] Start Kafka + Zookeeper (or KRaft), MLflow, etc., locally (docker-compose or kind)
- [ ] Implement infra helpers:
  - [ ] `deployment_profiles.py` final versions
  - [ ] `networking/haproxy_config.py` and templates
  - [ ] `networking/vpn.py` and templates
- [ ] Document infra usage in `docs/architecture.md` and `docs/governance.md` as "how to deploy dev stack"

### Acceptance Criteria

- [ ] `fednestd messaging bootstrap-topics --config messaging.yaml` successfully creates topics in local Kafka
- [ ] `fednestd infra generate-haproxy-config` and `generate-vpn-config` produce valid files
- [ ] `dev_start_cluster.sh` spins up a usable dev environment

---

## Milestone 5 – Federation Control Plane (FedServer + Edge Client Skeleton)

**Goal:** Wire a basic federation loop with Flower/custom server + edge client, without heavy nested learning logic yet.

### Key Tasks

- [ ] Implement `federation/server.py`:
  - [ ] Basic FedServer (Flower or custom) that:
    - [ ] Exposes endpoint(s) behind HAProxy
    - [ ] Can broadcast current model version
- [ ] Implement `federation/client.py`:
  - [ ] Edge client that:
    - [ ] Connects to FedServer (or Kafka control topic)
    - [ ] Downloads model checkpoint or metadata
    - [ ] Calls `training.tier2_trainer.run_edge_round` (stub)
- [ ] Integrate Kafka control topic:
  - [ ] `control.federation_rounds` for `RoundStart`, `ModelAvailable`

### Acceptance Criteria

- [ ] Local demo: Tier 1 (server) + one Tier 2 (client) run in Docker or on localhost
- [ ] You can see:
  - [ ] Round started → edge client receives event → prints or logs that it would train
  - [ ] `ΔW_experts_local` messages produced (even dummy payloads) to Kafka

---

## Milestone 6 – Edge Adapters Training & Local Sidecar Governance

**Goal:** Make Tier 2/3 actually train LoRA/QLoRA adapters and enforce local governance sidecar.

### Key Tasks

- [ ] `training/tier2_trainer.py`:
  - [ ] Implement adapter-only training loop:
    - [ ] Load frozen `W_core`, `W_experts`
    - [ ] Attach adapters
    - [ ] Train on local dataset (dummy or real JSONL)
- [ ] `governance/local_sidecar.py`:
  - [ ] Implement:
    - [ ] Policy evaluation of outbound payloads
    - [ ] Blocking of anything that's not ModelDelta-like
    - [ ] Local audit logging (file-based)
  - [ ] Wire sidecar into `federation/client.run_edge_client`:
    - [ ] All outbound deltas go through sidecar
    - [ ] Apply potential DP noise / hashing if configured

### Acceptance Criteria

- [ ] Edge node can:
  - [ ] Receive model, train adapters for N steps, generate `ΔW_experts_local`
  - [ ] Sidecar logs decisions
  - [ ] `updates.experts.local` topic receives real-ish delta messages (even if compressed/placeholder for now)

---

## Milestone 7 – Aggregation Logic & Nested Learning Behavior

**Goal:** Implement real aggregation logic that respects nested learning + hierarchical tiers.

### Key Tasks

- [ ] `training/aggregation.py`:
  - [ ] Implement:
    - [ ] Combining `ΔW_experts_T1` and `ΔW_experts_local` from Kafka
    - [ ] Version-aware weighting (downweight stale updates)
    - [ ] Optionally reliability weighting per client
  - [ ] Implement simple nested learning / anti-forgetting strategies:
    - [ ] Regularization term between current experts and previous version
    - [ ] Option for EWC-like penalty or knowledge distillation to earlier versions
- [ ] Add evaluation in `training/evaluation.py`:
  - [ ] Per-version metrics
  - [ ] Basic regression checks vs previous version

### Acceptance Criteria

- [ ] End-to-end: Tier1 core update + edge updates + aggregation produces a new model version v+1
- [ ] You can observe:
  - [ ] Model version increments
  - [ ] Differences in expert weights
  - [ ] Basic metrics comparison vs v

---

## Milestone 8 – Observability & Data Engine Loop

**Goal:** Have a good observability story and a basic data engine feedback loop.

### Key Tasks

- [ ] `observability/metrics.py`:
  - [ ] Expose Prometheus metrics for:
    - [ ] Number of active edge clients
    - [ ] Training time per round
    - [ ] Aggregation frequency
    - [ ] Kafka lag for relevant topics
- [ ] `observability/tracing.py`:
  - [ ] Optional: add OpenTelemetry spans around key flows (aggregation, training)
- [ ] Implement a lightweight "data engine" consumer:
  - [ ] Read from `telemetry.edge`
  - [ ] Identify, for example, high-loss segments or slow devices
  - [ ] Emit new `tasks.training` messages targeting specific clients or segments
- [ ] Dashboards:
  - [ ] Grafana dashboards for:
    - [ ] Training metrics
    - [ ] Kafka throughput
    - [ ] Edge participation

### Acceptance Criteria

- [ ] Grafana shows meaningful charts from a dev run
- [ ] A telemetry-based trigger can generate a follow-up training task (even in simple form)

---

## Milestone 9 – E2E Integration Scenario (Demo-able System)

**Goal:** Have a single reproducible demo that runs the full stack on a laptop or small cluster.

### Key Tasks

- [ ] Compose a demo script:
  - [ ] Start infra: Kafka, MLflow, etc.
  - [ ] Start FedServer + Tier 1 training worker
  - [ ] Start N edge clients (containers)
  - [ ] Run:
    - [ ] 1 core update
    - [ ] 1–2 edge rounds
    - [ ] 1 aggregation step
- [ ] Provide example data:
  - [ ] Small JSONL dataset and config for Tier1 and Tier2
- [ ] Ensure all pieces (governance, observability, messaging, training) are visible in logs and dashboards

### Acceptance Criteria

- [ ] A new contributor can:
  - [ ] Clone repo
  - [ ] Follow `examples/minimal_tier1_cluster.md`
  - [ ] Run the demo script
  - [ ] See model versions evolving and logs/metrics/telemetry flowing

---

## Milestone 10 – Documentation & "0.1.0" Release

**Goal:** Polish docs and cut a tagged release.

### Key Tasks

- [ ] Docs:
  - [ ] `docs/architecture.md` – finalize with current reality
  - [ ] `docs/governance.md` – dual governance story and configuration
  - [ ] `docs/api_reference.md` – public Python API (model + training + federation)
  - [ ] `docs/cli.md` – final CLI reference (all commands/flags)
- [ ] Update `README.md`:
  - [ ] Clear "What this is", "What this isn't", and "Quickstart"
- [ ] Tag v0.1.0 and publish:
  - [ ] Optionally to a private PyPI or artifact repo

### Acceptance Criteria

- [ ] Docs build cleanly (via mkdocs or similar if you're using it)
- [ ] A fresh user can follow README + docs, run the demo, and understand the architecture

---

## Notes

- This roadmap is organized for clarity and can be adapted to your timeline
- Each milestone builds on previous ones, but some tasks can be parallelized within milestones
- Consider breaking down larger tasks into smaller subtasks as you work through each milestone
- Regular check-ins against acceptance criteria will help ensure quality at each stage

