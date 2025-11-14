# SysMoBench: Evaluating AI on Formally Modeling Complex Real-World Systems

## Scenario Description

Formal models are essential to specifying large, complex computer systems and verifying their correctness, but are notoriously expensive to write and maintain. SysMoBench evaluates whether LLM-powered agents can translate realistic system artifacts into executable TLA+ specifications that pass rigorous syntactic, semantic, and invariant checks.

![SysMoBench Overview](sysmobench_core/docs/pic/overview.png)

### Task Details

- **Input**
  - System source code plus task-specific prompts and invariants from `sysmobench_core/tla_eval/tasks/<task_name>/`
  - Agent parameters (method, model name, iteration budget)
  - TLA+ evaluation configuration and trace data
- **Output**
  - Generated TLA+ specification (`GenerationResult.tla_specification`)
  - Iterative correction summaries with compilation/runtime verdicts
- **Evaluation**
  - `compilation_check` / `action_decomposition` (syntax correctness via SANY)
  - `runtime_coverage` (TLC simulation coverage)
  - `trace_validation` / `pgo_trace_validation` (conformance to real system traces)
  - `invariant_verification` (system-specific safety/liveness properties)

### Key Features

- Automated four-phase evaluation pipeline covering syntax, runtime, trace conformance, and invariants
- Nine real-world concurrent and distributed systems (Etcd Raft, Redis Raft, Asterinas primitives, Xline CURP, PGo suites)
- Extensible configuration for adding new systems via prompts, traces, and invariant templates

## Benchmark Setup

### Prerequisites

- Python 3.9+
- Java 11+ (SANY/TLC binaries are downloaded during installation)
- Anthropic evaluator key (required for trace/invariant workflows)
- LLM credentials for the model under test (OpenAI, Azure OpenAI, Anthropic, etc.)

### Configuration

Edit `benchmarks/sysmobench/env.toml`:

```toml
[evaluator_api_keys]
ANTHROPIC_API_KEY = "your_evaluator_key"

[llm]
OPENAI_API_KEY = "your_openai_key"
AZURE_API_KEY = "your_azure_key"
AZURE_API_BASE = "https://your-azure-endpoint.openai.azure.com"
AZURE_API_VERSION = "2024-05-01-preview"
ANTHROPIC_API_KEY = "your_model_key"

[hardware]
use_gpu = false

[env-docker]
image = "default"
entrypoint = "./run.sh"
```

### Install Dependencies

```bash
cd benchmarks/sysmobench
./install.sh
```

This script installs OpenJDK when necessary, creates `.venv/`, installs `benchmarks/sysmobench/requirements.txt`, registers `sysmobench_core` in editable mode (exposing `sysmobench`/`sysmobench-setup`), and downloads the TLA+ toolchain.

### Run the Benchmark

```bash
./run.sh <model_name>
```

The wrapper executes `src/main.py` with the default task list from `data/benchmark/tasks.jsonl`, iterating up to three correction rounds per task. Results are stored at:

```
outputs/sysmobench__<model>__agent_based__<timestamp>/
├── result.jsonl   # Line-delimited iteration summaries per task
└── avg_score.json # Final averaged score across tasks
```

### Use the SysCap CLI (optional)

To orchestrate SysMoBench alongside other benchmarks:

```bash
cd cli
./run_all_local.sh <model_name>
```

### Using the upstream SysMoBench CLI (optional)

```bash
cd benchmarks/sysmobench
source .venv/bin/activate
sysmobench --task spin --method agent_based --model <model> --metric compilation_check
sysmobench --list-tasks
deactivate
```

For exhaustive CLI flag descriptions, see [Usage Guide](sysmobench_core/docs/Usage.md).

## Benchmark Tasks

SysMoBench includes 9 diverse real-world system artifacts from concurrent and distributed systems:

| System | Type | Description | Source Lang. | Source LoC | TLA+ LoC |
|--------|------|-------------|--------------|------------|----------|
| Asterinas Spinlock | Concurrent | Synchronization | Rust | 213 | 151 |
| Asterinas Mutex | Concurrent | Synchronization | Rust | 186 | 219 |
| Asterinas Rwmutex | Concurrent | Synchronization | Rust | 395 | 250 |
| Etcd Raft | Distributed | Consensus (Raft) | Go | 2,159 | 385 |
| Redis Raft | Distributed | Consensus (Raft) | C | 2,394 | 349 |
| Xline CURP | Distributed | Replication (CURP) | Rust | 4,064 | 100 |
| PGo dqueue | Distributed | Distributed Queue | Go | 175 | 75 |
| PGo locksvc | Distributed | Lock Server | Go | 281 | 93 |
| PGo raftkvs | Distributed | Consensus (Raft) | Go | 3,163 | 508 |

To list all available tasks:

```bash
sysmobench --list-tasks
```

## Evaluation Metrics

SysMoBench provides four automated phases to evaluate AI-generated TLA+ models with different metrics:
   syntax correctness, runtime correctness, conformance to system implementation, and invariant correctness.

![Evaluation Workflow](sysmobench_core/docs/pic/SysMoBench.png)

### Reproducing Paper Results

The paper uses the following metrics for evaluation:

1. **Syntax Correctness**: Weighted combination (50% each) of `compilation_check` and `action_decomposition`
2. **Runtime Correctness**: `runtime_coverage`
3. **Conformance to System Implementation**:
   - Non-PGo systems (spin, mutex, rwmutex, etcd, redis, xline): `trace_validation`
   - PGo systems (raftkvs, locksvc, dqueue): `pgo_trace_validation`
4. **Invariant Correctness**: `invariant_verification`

### 1. Syntax Correctness

Validates that the generated TLA+ model adheres to TLA+ grammar rules, correct operator usage, and proper module structure using the SANY Syntactic Analyzer. The evaluation includes both full-model compilation and per-action analysis to provide fine-grained feedback on syntax errors.

**Available metrics:**
- `compilation_check` - Basic TLA+ compilation checking using SANY parser
- `action_decomposition` - Evaluate individual actions separately for better granularity

### 2. Runtime Correctness

Evaluates whether the syntactically correct model can execute without runtime errors. The TLC Model Checker performs bounded model checking and simulation to explore the state space without invariant checking, recording covered actions and any runtime errors encountered (e.g., type mismatches, invalid operations).

**Available metrics:**
- `runtime_check` - Model checking with TLC
- `coverage` - TLA+ specification coverage analysis using TLC coverage statistics
- `runtime_coverage` - Runtime coverage using simulation mode to identify successful vs error-prone actions

### 3. Conformance to System Implementation

Measures whether the model conforms to actual system behavior through trace validation. Execution traces collected from instrumented system code are validated against the model to verify if each trace corresponds to a valid path in the model's state space, ensuring behavioral consistency between model and implementation.

**Available metrics:**
- `trace_validation` - Full trace generation and validation pipeline
- `pgo_trace_validation` - Full trace generation and validation pipeline (PGo version)

### 4. Invariant Correctness

Verifies that the model satisfies system-specific safety and liveness properties. Using expert-written invariant templates that are automatically concretized for the generated model, TLC model checking validates correctness properties such as mutual exclusion, log consistency, and progress guarantees across the explored state space.

**Available metrics:**
- `invariant_verification` - Model checking with invariants

## Adding New Systems

SysMoBench is designed to be extensible. To add a new system artifact:

1. **Prepare system artifact**: Collect repository links, branch names, and any relevant materials
2. **Create task definition**: Specify modeling requirements, task configuration and related files in `task.yaml` and define invariant templates for correctness properties
3. **Instrument for trace collection**: Add logging statements to system code to collect execution traces for conformance validation

For detailed instructions, see [Adding New Systems Guide](sysmobench_core/docs/add_new_system.md).


## Project Structure

```
LLM_Gen_TLA_benchmark_framework/
├── scripts/
│   └── run_benchmark.py          # Main entry script for running benchmarks
├── tla_eval/
│   ├── tasks/                    # Task definitions for each system artifact
│   │   ├── spin/                 # Spinlock task with prompts, configs
│   │   │   ├── prompts/          # System-specific prompts
│   │   │   └── task.yaml         # Task configuration (system info)
│   │   ├── mutex/
│   │   └── ...
│   ├── models/                   # LLM model interfaces and wrappers
│   ├── evaluation/               # Evaluator implementations organized by metric type
│   └── config.py                 # Configuration management (API keys, LLM model configs)
├── data/
│   ├── invariant_templates/      # Expert-written invariant templates for each system
│   └── traces/                   # System execution traces for conformance evaluation
└── lib/                          # TLA+ toolchain (tla2tools.jar for SANY and TLC)
```
