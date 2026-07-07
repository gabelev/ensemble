# ensemble

**A domain-agnostic framework for creative multi-agent systems.**

`ensemble` is the reusable creative-agent layer: personas that drift, a
stigmergic ledger from which a theme *precipitates* instead of being chosen, a
deterministic authoring pipeline, taboo (anti-repetition) memory, a
primitive-composition engine for design, and a taste discriminator that rejects
competent-generic work.

It ships **mechanisms**; you supply the **content**.

An **instance** is a concrete creative product built on ensemble:

- **[mold](https://github.com/gabelev/mold)** — an autonomous web zine about AI
  culture (the first instance; content lands in
  [terrarium](https://github.com/gabelev/terrarium)).
- **putu.ai** — expected second instance.

> **The boundary rule.** Nothing instance-specific lives here. No single
> product's aesthetic, data source, or personas. The dependency arrow points one
> way: instances import `ensemble`; `ensemble` imports nothing back.

## Architecture

Every agent runs the same loop; every issue/cycle runs the same pipeline:

```
                        ┌──────────────────────────────┐
   agent loop           │   PERCEIVE → DECIDE →        │
   (ensemble.agent)     │   EXECUTE → PUBLISH          │
                        └──────────────────────────────┘

   pipeline (ensemble.pipeline — deterministic DAG, not work-stealing)

   ┌──────────┐   ┌─────────────────┐   ┌────────┐   ┌────────┐   ┌────────┐   ┌─────────┐
   │ planning │ → │ authors 1..N    │ → │ editor │ → │ design │ → │ verify │ → │ publish │
   │          │   │ (parallel)      │   │        │   │        │   │        │   │         │
   └────┬─────┘   └─────────────────┘   └────────┘   └───┬────┘   └────────┘   └────┬────┘
        │                                                │                          │
        ▼                                                ▼                          ▼
   ┌──────────────────┐                     ┌──────────────────────┐      ┌──────────────────┐
   │ stigmergic ledger│                     │ primitive library +  │      │ VCS adapter      │
   │ fragments accrete│                     │ composer + taboo +   │      │ (QA/PROD branch) │
   │ densest cluster  │                     │ discriminator        │      │ → deploy adapter │
   │   = the theme    │                     └──────────────────────┘      └──────────────────┘
   └──────────────────┘
```

The load-bearing ideas:

- **The theme emerges.** Fragments accrete in a ledger; the densest cluster at
  deadline *is* the theme. A planner names what precipitated — it never invents
  a theme top-down. (`ensemble.ledger.precipitate_theme`)
- **Drift + taboo keep it moving.** Cycle N's state is downstream of cycle
  N−1's residue; the moves used this cycle are forbidden next cycle. The target
  moves, so the discriminator can't be gamed. (`ensemble.state`)
- **Taste is over-determined.** The discriminator runs N judges, each anchored
  to a *different* external reference (same-lineage disagreement is fake), and
  requires passing **all** anchors — never a single scalar a generator could
  climb. It rejects the *absence* of mistakes: regenerate riskier, not more
  polished. (`ensemble.taste`)
- **Everything external is an adapter.** Models, storage, VCS, deploy — all
  behind protocols, all injectable, all mockable. The core has **zero runtime
  dependencies**.

## Layout

```
ensemble/
  agent.py            Agent ABC, Persona, SelfState, the PDE loop
  memory.py           EpisodicMemory protocol + in-memory impl
  ledger.py           Fragment, Ledger, Clusterer, theme precipitation
  pipeline.py         Stage, Pipeline, parallel fan-out (native runner)
  state/
    persona.py        versioned JSON state store
    drift.py          DriftEngine protocol (state N ← state N−1 + residue)
    taboo.py          TabooMemory — the anti-repetition store
  design/
    primitive.py      Primitive protocol + PrimitiveLibrary
    composer.py       select → parametrize → assign-by-stance → taboo → constrain
  taste/
    judge.py          Judge protocol, ScoreVector (never collapsed to a scalar)
    discriminator.py  pass-all panel + warm-start human-pick hook
  providers/
    model.py          ModelProvider protocol + MockProvider (offline, deterministic)
  adapters/
    vcs.py            VCS protocol + LocalGitVCS (QA/PROD branch commits)
    deploy.py         Deploy protocol
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design doc: each
abstraction's contract, what the framework owns vs. what an instance owns, and
how adapters graduate from instance to framework.

## How an instance plugs in

```python
from ensemble.agent import Agent, Persona
from ensemble.ledger import precipitate_theme
from ensemble.pipeline import Pipeline

class MyAuthor(Agent):                      # 1. subclass Agent per persona
    def perceive(self, ctx): ...
    def decide(self, perception): ...
    def execute(self, decision): ...        #    (model calls go through self.model)

cfg = build_config()                        # 2. one composition root binds adapters:
                                            #    ledger, VCS, deploy, model provider
pipeline = (Pipeline()                      # 3. assemble the deterministic DAG
    .then("planning", planning_stage)
    .then("authors", authors_stage)         #    parallel fan-out inside
    .then("editor", editor_stage)
    .then("publish", publish_stage))
ctx = pipeline.run()
```

The instance owns: persona prompts, primitives, judges/corpora, adapter
bindings, and the drifting state files (typically versioned in a public content
repo so drift is diff-able). ensemble owns everything mechanical.

## Development

```bash
uv sync --extra dev
uv run pytest
```

The core is dependency-free and fully testable offline (`MockProvider`,
`InMemoryLedger`, `LocalGitVCS`).

## License

AGPL-3.0-or-later — the network-use clause is deliberate: instances are hosted
autonomous services. See [LICENSE](LICENSE) and [NOTICE](NOTICE) for
third-party model/font terms.
