# fednestd

## Installation

### Prerequisites

- Python 3.10 or higher
- pip

### Basic Installation

For Tier 2/3 (edge devices) or basic usage:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### Tier 1 Installation (with DeepSpeed)

DeepSpeed requires PyTorch to be installed first. Install in this order:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install PyTorch first (required for DeepSpeed build)
pip install torch>=2.0

# Then install the package with Tier 1 dependencies
pip install -e ".[tier1]"
```

Alternatively, install everything in one step (PyTorch will be installed first automatically):

```bash
pip install torch>=2.0
pip install -e ".[tier1]"
```

### Development Installation

For development with testing and linting tools:

```bash
pip install -e ".[tier1,dev]"
```

---

# Federated Nested MoE Framework – Architecture & Project Plan

## 1. Context & Objectives

This document describes the design of a **federated, nested-learning framework** that:

*   Trains **Mixture-of-Experts (MoE)** models across **heterogeneous compute tiers**:
    *   **Tier 1:** HPC clusters / data centers.
    *   **Tier 2/3:** Edge devices (IoT, vehicles, mobiles).
*   Uses **Nested Learning** concepts to enable **continual learning** without catastrophic forgetting.
*   Ensures strict **data privacy** and **governance**:
    *   **Global governance** in data centers (DataHub, Apache Ranger, Flyte, MLflow).
    *   **Local, airgapped governance** on edge devices (sidecar).
*   Is orchestrated with **Flyte** and coordinated via **Flower** (or similar FL framework).
*   Uses **Kafka** for event streaming and **HAProxy/VPN** for secure connectivity.
*   Exposes a **CLI-first, modular Python framework** that can later be wrapped as a service/app.

This document is intended for **project planning**, implementation, and infra design.

---

## 2. Requirements Recap

### Functional Requirements

1.  **Federated Training Across Multiple Clusters**
    *   Training must occur in a federated fashion across multiple clusters (Tier 1) and devices (Tier 2/3).
    *   No raw data leaves any cluster or device by default.

2.  **Heterogeneous Node Types**
    *   Nodes can be:
        *   **Servers / HPC clusters** (Tier 1).
        *   **IoT devices, vehicles, mobile devices** (Tier 2/3).
    *   Mixed hardware and network conditions.

3.  **Tier-Specific Training Capabilities**
    *   **Tier 1:**
        *   Train **core** foundational model.
        *   Train **MoE experts** (feed-forward networks).
        *   Can also train LoRA/QLoRA adapters if desired.
    *   **Tier 2/3:**
        *   Train **only local adapters** (LoRA/QLoRA-like for experts).
        *   Core weights stay frozen.

4.  **Hierarchical Asynchronous Co-Training**
    *   Multiple nested loops:
        *   Fast, local training at edge.
        *   Slower, heavy training at Tier 1.
        *   Event-driven aggregation and model versioning.
    *   No strict synchronous rounds required; system must tolerate stale updates.

5.  **Nested Learning Principle**
    *   Treat global training as an **outer optimization**.
    *   Treat per-node training (especially adapters) as **nested inner optimizations**.
    *   Design to **mitigate catastrophic forgetting**.

6.  **Data & Privacy**
    *   Data should **not leave** its cluster or device unless explicitly allowed.
    *   Common format: **JSONL** for LLM fine-tuning.
    *   PII detection / anonymization where any text leaves local boundaries.

7.  **Governance & Compliance**
    *   **Global governance**: DataHub, Apache Ranger, MLflow, Flyte.
    *   **Local governance**: Sidecar per edge node, airgapped, no central metadata leakage.

8.  **Model Versioning & Observability**
    *   Automated **model versioning** (MLflow).
    *   **Monitoring** & **observability** for training, infra, and telemetry.

9.  **Scalable Eventing & Networking**
    *   **Kafka** for control and update streams.
    *   **HAProxy** and **VPN** for secure connectivity from edge to central infra.

10. **Developer Experience**
    *   Primary interface: **CLI** + Python library.
    *   Later: optional API service / UI.

---

## 3. High-Level Architecture

### 3.1 Tiers

*   **Tier 1 – HPC / Data Center**
    *   Runs **full MoE model**: core + experts.
    *   Heavy distributed training (DeepSpeed + PyTorch).
    *   Full integration with global control plane:
        *   Flyte (orchestration).
        *   DataHub (metadata).
        *   Apache Ranger (data access control).
        *   MLflow (runs & model registry).
        *   Observability stack (Prometheus, Grafana, logs, tracing).

*   **Tier 2/3 – Edge Nodes (IoT / Vehicles / Mobiles)**
    *   Receive **frozen global model** snapshot (quantized if necessary).
    *   Train **only expert adapters (LoRA/QLoRA)**.
    *   Use local governance sidecar:
        *   Enforce “model-delta-only” export.
        *   Maintain local audit logs, never shipped centrally.

### 3.2 Nested Learning & Co-Training

Three nested loops:

1.  **Inner Loop (Edge / Local Adapters)**
    *   Each device trains adapters on its own data.
    *   Produces `ΔW_experts_local` (adapters-only deltas).
2.  **Middle Loop (Tier 1 / Core & Experts)**
    *   Clusters train:
        *   Core `W_core` on global data.
        *   Experts `W_experts_global` on large-scale datasets.
    *   Integrate `ΔW_experts_local` from edge nodes.
3.  **Outer Loop (Global Control Plane)**
    *   Flyte orchestrates:
        *   When to do core updates.
        *   When to aggregate expert updates.
        *   When to evaluate & promote new model versions.
    *   Data Engine-like feedback to generate new tasks.

---

## 4. Model Design

### 4.1 Parameter Partitioning

We explicitly partition model parameters:

1.  **Core (`W_core`)**
    *   Token & positional embeddings.
    *   Self-attention weights (Q, K, V, O).
    *   Normalization layers (LayerNorm, RMSNorm).
    *   Optionally gating network weights (if we don’t want devices to alter routing).
2.  **Global Experts (`W_experts_global`)**
    *   Set of feed-forward experts: `{W_E1, W_E2, ..., W_En}`.
    *   Hosted and trained primarily at Tier 1.
    *   Sharded and parallelized using DeepSpeed MoE.
3.  **Adapters / LoRA Layers**
    *   **Tier 1 Adapters (optional)**: Domain-specific adapters for specific clusters or datasets.
    *   **Tier 2/3 Adapters (mandatory)**: Low-rank matrices `(A_i, B_i)` on top of expert weights:
        *   `W_Ei_eff = W_Ei + A_i · B_iᵀ`
        *   Only `(A_i, B_i)` trainable on edge nodes.

### 4.2 Routing / Gating

*   **Global gating network** `g(x; W_gate)`:
    *   Trained at Tier 1 on large-scale data.
*   **On Tier 2/3**:
    *   *Option 1:* Gating fully **frozen**, only expert functions adapted via adapters.
    *   *Option 2:* Minimal gating adapters (e.g. per-expert bias) that stay **local only** and are not aggregated centrally.

---

## 5. Training Workflows

### 5.1 Tier 2/3 – Edge Adapters Loop

**Steps on each edge node:**

1.  **Receive Model Snapshot**
    *   Pull `W_core`, `W_experts_global`, and model version `v` via FedServer or Kafka control events.
    *   Optionally receive quantized weights (QLoRA / 4-bit for memory efficiency).
2.  **Initialize Local Model**
    *   Load frozen `W_core`, `W_experts_global`.
    *   Attach local adapters `(A_i, B_i)` for selected experts.
3.  **Local Training**
    *   Train with local private dataset (JSONL or equivalent).
    *   Objective: minimize local loss `L_local`, updating only adapters.
    *   Use resource-aware training: mixed precision, tiny batch sizes, small learning rates.
4.  **Governance Filtering**
    *   Sidecar validates outbound payload:
        *   Must be strictly `ΔW_experts_local` (or new adapter weights).
        *   No raw data, no detailed metadata, no PII.
    *   Sidecar writes local audit logs.
5.  **Send Update**
    *   `ΔW_experts_local` published to Kafka topic `updates.experts.local` via VPN + HAProxy.
6.  **Telemetry**
    *   Minimal training metrics & statuses (loss, success/failure) published to `telemetry.edge` topic (optionally DP-noised).

*This loop is **asynchronous**: Node trains when resources are available; central system ingests deltas continuously.*

### 5.2 Tier 1 – MoE Core & Experts Loop

**Inputs:** Global datasets, streams of `ΔW_experts_local`, configs/tasks.

**Steps:**

1.  **Core & Expert Training (CoreUpdate Workflow)**
    *   Flyte triggers a “core update” workflow.
    *   Ranger authorizes training services to access cluster data.
    *   DeepSpeed + PyTorch load `W_core`, `W_experts_global` and train on large-scale data.
    *   Compute `ΔW_core_T1`, `ΔW_experts_T1`.
2.  **Integrate Edge Expert Updates**
    *   Aggregation worker (FedServer or dedicated process) consumes `updates.experts.local`.
    *   Apply aggregation strategy (weight by recency, data size, reliability; downweight stale updates).
3.  **Global Parameter Update**
    *   Combine updates:
        ```text
        W_core    ← W_core    + η_core * ΔW_core_T1
        W_experts ← W_experts + η_T1   * ΔW_experts_T1
                              + η_T2   * ΔW_experts_agg_from_edges
        ```
4.  **Evaluation & Nested Learning Safeguards**
    *   Evaluate updated model on global validation sets and regressions.
    *   Apply anti-forgetting strategies: Regularization (EWC), selective freezing, or distillation.
5.  **Versioning & Promotion**
    *   Log run to MLflow; register new model version `v+1`.
    *   Update DataHub with lineage.
    *   Governance/SecOps approve or reject new version.
6.  **Broadcast New Version**
    *   FedServer / Kafka emits `ModelAvailable`/`RoundStart` for version `v+1`.

---

## 6. Governance & Privacy

### 6.1 Global Governance (Tier 1)

*   **Apache Ranger**: Defines and enforces data access policies. Audits data access.
*   **DataHub**: Central catalog of datasets, models, features. Maintains lineage (Dataset → Run → Model).
*   **MLflow**: Tracks experiments, metrics, artifacts. Model registry with stages.
*   **Flyte**: Orchestrates workflows (training, aggregation, eval). Encodes governance in pipeline definitions.
*   **Presidio**: PII detection/anonymization for exceptional cross-silo sharing.

### 6.2 Local Governance (Tier 2/3 – Sidecar)

**Sidecar responsibilities:**

*   **Policy Enforcement**: Local static config (YAML/JSON) or OPA-like rules defining allowed endpoints and payload fields.
*   **Outbound Filter**: Validates payloads (no raw text, no identifiers).
*   **Local Audit Logs**: Tracks local training/export events; stored on device only.
*   **Optional Local Presidio**: Lightweight PII detection for logs.

*This implements **dual governance**: Full-featured governance in Tier 1; Minimal, strictly enforced governance in Tier 2/3 with airgapped metadata.*

---

## 7. Networking & Connectivity

### 7.1 Components

*   **VPN (WireGuard / IPSec)**: Secure overlay for edge nodes to reach central cluster.
*   **HAProxy / Ingress**: Public ingress/load-balancer for FedServer/Kafka. Terminates TLS.
*   **mTLS & Auth**: Mutual TLS certificates/tokens binding identity (`client_id`) to connections.

### 7.2 Network Paths

*   **Edge Node**: `Edge Runtime → Sidecar → VPN Tunnel → VPN Gateway → HAProxy → FedServer / Kafka`
*   **Tier 1**: Internal communication within cluster (FedServer, Kafka, Flyte) behind firewall.

---

## 8. Messaging & Event Streaming (Kafka)

### 8.1 Core Topics

1.  `control.federation_rounds`: Events: `RoundStart`, `ModelAvailable`, config updates.
2.  `updates.experts.local`: Payload: `ΔW_experts_local` + minimal metadata.
3.  `telemetry.edge`: Payload: Aggregated loss metrics, training outcome (DP/noise optional).
4.  `tasks.training`: Payload: Structured `TrainingTask` objects (core_update, expert_aggregation).

### 8.2 Benefits

*   **Loose coupling**: Decouples training, aggregation, and orchestration.
*   **Replayability**: Allows reconstruction of training history/debugging.
*   **Data Engine**: Telemetry feeds analytics which drive new tasks.

---

## 9. Tooling & Library Stack

| Category | Tools |
| :--- | :--- |
| **Training & Modeling** | **PyTorch** (Core DL), **DeepSpeed** (Distributed MoE), **PEFT/LoRA/QLoRA** (Adapters), **ONNX** (Export). |
| **Federation** | **Flower** (FL Server/Client abstractions), **Flyte** (K8s-native orchestration). |
| **Governance** | **Apache Ranger** (Access control), **DataHub** (Catalog/Lineage), **MLflow** (Registry), **Presidio** (PII). |
| **Observability** | **Prometheus** (Metrics), **Grafana** (Dashboards), **Loki** (Logs), **OpenTelemetry** (Tracing). |
| **Networking** | **Kafka** (Streaming), **HAProxy** (Ingress), **WireGuard/IPSec** (VPN). |

---

## 10. Codebase & Packaging Plan

Primary project: **CLI-first Python package** (can later host a service).

### 10.1 High-Level Layout

```text
federated-nested-moe/
├── pyproject.toml            # packaging, dependencies, entrypoints
├── README.md                 # high-level docs
├── docs/                     # detailed doc for architecture, governance, etc.
├── examples/                 # sample configs, Flyte workflows, Dockerfiles
├── src/
│   └── fednested/
│       ├── cli.py            # main CLI (typer/click)
│       ├── config/           # Pydantic models and config loader
│       ├── model/            # MoE model, adapters, checkpoints, quantization
│       ├── training/         # tier1_trainer, tier2_trainer, aggregation
│       ├── federation/       # Flower-based server/client wrappers
│       ├── governance/       # ranger, datahub, local_sidecar, presidio integration
│       ├── orchestration/    # Flyte helpers, reference workflows
│       ├── observability/    # logging, metrics, tracing
│       ├── messaging/        # kafka_client, topic management, events
│       ├── networking/       # vpn tools, haproxy templates, security helpers
│       └── utils/            # generic utilities
└── tests/
    └── ...                   # unit/integration tests
```

### 10.2 Key Modules & Responsibilities

*   **`fednested.model`**
    *   `moe_model.py`: Definition of MoE architecture and parameter partitioning.
    *   `adapters.py`: LoRA/QLoRA layers and APIs.
    *   `checkpointing.py`: Load/save state_dicts, split/merge core/experts/adapters.
*   **`fednested.training`**
    *   `tier1_trainer.py`: Orchestrates deep MoE training on HPC (DeepSpeed).
    *   `tier2_trainer.py`: Edge training loops (adapters only).
    *   `aggregation.py`: Logic for combining `ΔW_experts`.
*   **`fednested.federation`**
    *   `server.py`: Custom FedServer hooks into Kafka & aggregation.
    *   `client.py`: Edge client runtime.
*   **`fednested.governance`**
    *   `local_sidecar.py`: Local enforcement engine.
    *   `global_metadata.py`: DataHub + MLflow hooks.
*   **`fednested.orchestration`**
    *   `flyte_integration.py`: Tasks wrapping CLI calls.

### 10.3 CLI Design

We use Typer or Click for a clean CLI.

*   `fednested init-config tier1`
    *   Generate sample Tier 1 config (model, data, Ranger, MLflow settings).
*   `fednested tier1 core-update --config config/tier1.yaml`
    *   Run a Tier 1 core + experts training cycle.
*   `fednested tier1 aggregate-experts --config config/tier1.yaml`
    *   Run aggregator: consume `updates.experts.local`.
*   `fednested tier2 run-client --config config/tier2.yaml`
    *   Start edge client: join federation, train local adapters, send deltas.
*   `fednested messaging bootstrap-topics`
    *   Create required Kafka topics.
*   `fednested infra generate-vpn-config --profile edge`
    *   Generate VPN client config for edge node enrollment.

---

## 11. Deployment Profiles

### 11.1 Tier 1 – Cluster Deployment
*   **Environment:** Kubernetes or HPC cluster with GPU nodes.
*   **Components:** Flyte, Kafka, FedServer, HAProxy, DataHub, MLflow, Ranger.
*   **Execution:** Run as K8s Jobs using `tier1_trainer.py` with DeepSpeed.

### 11.2 Tier 2/3 – Edge Deployment
*   **Environment:** IoT devices, vehicles, mobiles (Container or native).
*   **Components:** `fednested` client library, Local Sidecar, VPN client.
*   **Constraints:** Model quantization (QLoRA), energy-aware scheduling.

---

## 12. Roadmap & Phased Delivery

1.  **Phase 1 – Core Framework & Tier 1 Only**
    *   Implement MoE model + adapters.
    *   Implement Tier 1 training with DeepSpeed.
    *   Integrate MLflow + DataHub + Ranger.

2.  **Phase 2 – Federated Edge Training + Dual Governance**
    *   Implement edge client + adapters-only training.
    *   Implement sidecar governance.
    *   Configure VPN + HAProxy + Kafka.

3.  **Phase 3 – Nested Learning Optimizations & Data Engine**
    *   Add anti-forgetting strategies.
    *   Implement smarter aggregation schemes.
    *   Implement telemetry consumer & Data Engine.

4.  **Phase 4 – Optional Control Plane Service / UI**
    *   FastAPI service for listing models/tasks.
    *   Web UI for monitoring and governance approvals.

---

## 13. Risks & Considerations

*   **Complexity:** Managing Flyte, Flower, Kafka, Ranger, DataHub, etc. requires strong automation/IaC.
*   **Edge Resources:** Aggressive quantization is likely required.
*   **Security:** Adversarial clients could poison training; robust mTLS and sidecars are essential.
*   **Governance Consistency:** Dual pipelines must encode consistent policies despite using different tools.
