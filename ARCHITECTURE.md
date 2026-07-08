# ensemble — architecture

`ensemble` is a **domain-agnostic framework for creative multi-agent systems**. It
ships *mechanisms*; an *instance* ships *content*. Mold (an autonomous web zine
about AI culture) is the first instance; afar.music is expected to be the second.

> **The boundary rule.** Nothing about any single instance may leak into
> `ensemble`. No Mold aesthetic, no Suno, no petri palette, no masthead personas.
> Litmus test: if a symbol names an instance-specific thing, it belongs in the
> instance, not here. If you find yourself hardcoding an instance detail into
> `ensemble`, stop — move it to the instance.

## Why a framework at all

The reusable value is not "call an LLM in a loop." It is the *creative-agent
layer*: personas that drift, a stigmergic ledger from which a theme
**precipitates** instead of being chosen, a deterministic authoring pipeline, an
anti-repetition (taboo) memory that keeps output moving, a primitive-composition
engine for design, and a taste discriminator that rejects competent-generic
work. Those mechanisms are domain-independent. The music, the palette, the voice
— those are the instance's.

## Core abstractions

Each is a small protocol/ABC in `ensemble`; the instance supplies the content.

### 1. Agent — `ensemble/agent.py`
A persona running **PERCEIVE → DECIDE → EXECUTE → PUBLISH**. Carries a static
`Persona` (base prompt + personality), a drifting `SelfState`, an
`EpisodicMemory`, and a `ModelProvider`. Instances subclass `Agent` per role
(planner, author, editor, designer, verifier, publisher). ensemble provides the
loop and the contracts; the *voices* are the instance's.

### 2. Ledger (stigmergic) — `ensemble/ledger.py`
Fragments accrete; the **densest cluster is the theme** — nobody picks it, it
precipitates. `Ledger` is a storage protocol (append/read over a time window);
`Clusterer` is the precipitation algorithm over an injected embedder. The
ledger stores *textual* fragments, so clustering is generic; any heavy
domain-specific perception (e.g. audio embeddings) happens **upstream** in the
instance, before a fragment is written. This keeps the ledger clean.
Mold binds `Ledger` to Chaos Dimension; tests bind it to an in-memory store.

### 3. Pipeline — `ensemble/pipeline.py`
A **deterministic DAG**, not work-stealing: planning → authors (parallel
fan-out) → editor → design → verify → publish. `Stage` wraps a callable;
`Pipeline` runs stages in order with one fan-out step. An ensemble-native runner
is the default (no heavy dependency in the core); a LangGraph backend can be
added as an optional adapter if control flow ever outgrows a linear DAG.

### 4. State + drift — `ensemble/state/`
`SelfState`/`StyleState` are versioned JSON blobs. `DriftEngine` computes
state *N* from state *N−1* plus the last cycle's residue (issue N is downstream
of issue N−1's obsession-drift). `TabooMemory` records the specific *moves* used
per cycle and forbids/penalizes reuse next cycle — the moving target that makes
the discriminator un-gameable. ensemble defines the stores and the drift
contract; the instance defines what a "move" or a "style knob" *is*, and the
drifting state is persisted in the instance's content repo so drift is
diff-able.

### 5. Design composition — `ensemble/design/`
`Primitive` is a parametrized, testable component (for Mold: a CSS/SVG move).
`PrimitiveLibrary` registers them; `Composer` selects a subset, parametrizes
within bounds, assigns primitives to sections **driven by the writer's declared
stance** (form-follows-opinion), applies taboo memory, and injects a per-cycle
constraint. ensemble owns the composition *logic*; the instance owns the
*primitives* and the target medium.

### 6. Taste harness — `ensemble/taste/`
`Discriminator` runs **N heterogeneously-grounded judges** (each anchored to a
*different* external reference so their disagreement is real), scores against
**over-determined anchors**, and requires a candidate to pass *all* of them —
never collapsing to a single scalar a generator could climb. It is empowered to
demand *riskier*, not more polished, output. A warm-start human-pick loop feeds
preference data until the discriminator reproduces the house taste, then the
human drops out. ensemble owns the harness; the instance owns the corpora,
anchors, and risk-floor.

### 7. Adapters — `ensemble/adapters/`, `ensemble/providers/`
Integrations are adapters behind protocols: `VCS` (persistence + QA/PROD
branches), `Deploy`, `ModelProvider` (chat + vision), `EpisodicMemory`.
ensemble ships the *truly generic* impls (local-git, in-memory, a mock model
provider). Instance-specific adapters (Mold's Chaos-Dimension ledger) start in
the instance and **graduate** to `ensemble.adapters` only when a second instance
needs them (rule of three). This keeps the framework's dependency surface
minimal.

## How an instance plugs in

1. Depend on `ensemble` as a package.
2. Subclass `Agent` for each persona — base prompts + personalities live here.
3. Register `Primitive`s into a `PrimitiveLibrary`; supply `Judge`s + corpora.
4. Bind adapters at a single **composition root** (`config.py`) via dependency
   injection: `Ledger→CD`, `VCS→GitHub`, `Deploy→Vercel`, `ModelProvider→Claude`.
5. Assemble the `Pipeline` from ensemble `Stage`s filled with instance agents.

`ensemble` imports nothing from the instance. The instance imports `ensemble`.
The dependency arrow points one way, always.

## Directory layout

```
ensemble/ensemble/
  agent.py            # Agent ABC, Persona, SelfState, the PDE loop
  memory.py           # EpisodicMemory protocol + InMemoryMemory
  ledger.py           # Fragment, Ledger, Cluster, Clusterer, theme precipitation
  pipeline.py         # Stage, Pipeline, native runner (parallel fan-out)
  state/
    persona.py        # versioned JSON state store
    drift.py          # DriftEngine protocol
    taboo.py          # TabooMemory
  design/
    primitive.py      # Primitive protocol, PrimitiveLibrary
    composer.py       # composition engine
  taste/
    judge.py          # Judge protocol
    discriminator.py  # multi-judge, over-determined, pass-all harness
  providers/
    model.py          # ModelProvider protocol + MockProvider
  adapters/
    vcs.py            # VCS protocol + LocalGitVCS
    deploy.py         # Deploy protocol
```

## Stack

Python (fits pgvector episodic memory + the MERT/CLAP audio work instances need
+ optional LangGraph), packaged with `uv`/`pyproject.toml`. Site shells (e.g.
Mold's terrarium) are Astro. No hard dependency on any model provider, vector
store, or orchestrator lives in the core — all are adapters.

## License

`ensemble` and instances built on it: **AGPL-3.0** (the network-use clause is
load-bearing for hosted autonomous services). Instance *content* repos (Mold's
`terrarium`): **CC0**. See `NOTICE` for third-party model/font terms.
