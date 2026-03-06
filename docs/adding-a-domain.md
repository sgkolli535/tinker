# Adding a New Domain to tinker

tinker's architecture separates domain-agnostic orchestration (the LangGraph pipeline, state management, vision nodes, report generation) from domain-specific modules (component databases, physics/validation models, prompt templates). Adding a new product domain means implementing a new `DomainAdapter` — the graph itself doesn't change.

---

## What You Need

| Artifact | Purpose | Example (synth_midi) |
|---|---|---|
| **DomainAdapter subclass** | Implements all abstract methods | `domains/synth_midi/adapter.py` |
| **Component database** | JSON files of known parts with specs | `domains/synth_midi/db/*.json` |
| **Physics/validation functions** | First-order constraint checks | `domains/synth_midi/physics/` |
| **Prompt templates** | Domain-specific LLM prompts | `domains/synth_midi/prompts/` |

---

## Step-by-Step Guide

### 1. Create the domain directory

```
backend/tinker/domains/your_domain/
    __init__.py
    adapter.py
    db/
        components_a.json
        components_b.json
    physics/
        __init__.py
        check_a.py
        check_b.py
        validation.py
    prompts/
        __init__.py
        classification.py
        component_id.py
        spatial_estimation.py
        tradeoff_analysis.py
        alternative_suggestions.py
```

### 2. Seed the component database

Create JSON files in `db/` with known components for your domain. Each entry needs at minimum:

```json
{
  "id": "unique_component_id",
  "type": "human-readable type name",
  "estimated_current_mA": 50.0,
  "estimated_cost_usd": 2.50
}
```

The `type` field is what fuzzy matching uses to link LLM-identified components to known specs. Add whatever domain-specific fields your physics checks need (e.g., `thermal_resistance_C_per_W`, `max_torque_Nm`, `flow_rate_CFM`).

**Aim for 10-50 entries per component category.** This is enough for meaningful matching and demo-quality results. Sources: datasheets, vendor catalogs, reference designs.

### 3. Write prompt templates

Each prompt template is a Python file that returns a string. The LLM receives this string and returns structured JSON.

**Required prompts:**

**`classification.py`** — System-level classification from photos.
```python
PROMPT = """
You are an expert {domain} engineer.
Classify this {product type} from the photo(s).
Return JSON:
{
  "category": "...",
  "form_factor": "...",
  "power_input": "...",
  "io_visible": [...],
  "apparent_use_case": "...",
  "confidence": float
}
"""
```

**`component_id.py`** — Identify visible components.
```python
def build_prompt(classification: dict) -> str:
    return f"""
Identify all visible components in this {classification.get('category', 'device')}.
Return JSON:
{{
  "components": [
    {{"name": "...", "count": int, "visible_details": "..."}}
  ],
  "io": [
    {{"name": "...", "count": int, "notes": "..."}}
  ]
}}
"""
```

**`spatial_estimation.py`** — Estimate physical dimensions using known components as scale references.

**`tradeoff_analysis.py`** — Analyze design trade-offs given components + validation results.

**`alternative_suggestions.py`** — Propose alternative configurations.

### 4. Implement physics/validation checks

Create domain-specific validation functions in `physics/`. The main entry point is a `validate()` function:

```python
def validate(matched_components: list[dict], spatial: dict) -> dict:
    # Run your domain checks
    # ...
    return {
        "system_valid": True,
        "estimated_total_current_mA": 420.0,
        # Add domain-specific metrics
        "checks": [
            {
                "name": "Check name",
                "value": "420mA / 500mA",
                "status": "pass",  # "pass" | "warn" | "fail"
                "note": "Human-readable explanation",
            }
        ],
        "bottlenecks": [...],
        "route": "valid",  # "valid" | "invalid_fixable" | "invalid_fatal"
    }
```

The `route` field controls the LangGraph conditional edge:
- `"valid"` — proceed to trade-off analysis
- `"invalid_fixable"` — loop back to component lookup (up to 2 retries)
- `"invalid_fatal"` — skip to report with errors

### 5. Implement the DomainAdapter

Subclass `tinker.domain.DomainAdapter` and implement all abstract methods:

```python
from tinker.domain import DomainAdapter

class YourDomainAdapter(DomainAdapter):
    def __init__(self):
        # Load your component DB files
        self.components_a = load_json(Path(__file__).parent / "db" / "components_a.json")
        self.pool = self.components_a + ...

    def get_classification_prompt(self) -> str:
        return CLASSIFY_PROMPT

    def get_component_id_prompt(self, classification: dict) -> str:
        return build_component_prompt(classification)

    def get_spatial_prompt(self, components: list[dict]) -> str:
        return build_spatial_prompt(components)

    def lookup_components(self, identified: list[dict]) -> list[dict]:
        # Fuzzy-match identified components against your DB pool
        # Use tinker.db.lookup.fuzzy_match()
        ...

    def validate_physics(self, components: list[dict], spatial: dict) -> dict:
        return validate(components, spatial)

    def get_tradeoff_prompt(self, components: list[dict], validation: dict) -> str:
        return build_tradeoff_prompt(components, validation)

    def get_alternatives_prompt(self, components: list[dict], validation: dict) -> str:
        return build_alternatives_prompt(components, validation)

    def suggest_alternatives(self, components: list[dict], validation: dict) -> list[dict]:
        # Return deterministic suggestions based on validation results
        # These get re-validated through validate_physics() automatically
        ...

    def get_domain_name(self) -> str:
        return "your_domain"
```

### 6. Wire it up

In `main.py`, add your domain as an option. Currently the domain is hardcoded:

```python
adapter = SynthMidiDomainAdapter()
```

To support multiple domains, you could select based on user input:

```python
ADAPTERS = {
    "synth_midi": SynthMidiDomainAdapter,
    "your_domain": YourDomainAdapter,
}
adapter = ADAPTERS[domain_name]()
```

### 7. Write tests

Add tests in `backend/tests/`:

```python
def test_your_domain_pipeline():
    state = {
        "images": [],
        "user_context": None,
        # ... full initial state
    }
    result = run_pipeline(state, YourDomainAdapter(), HeuristicLLMClient())
    assert result["final_report"]
    assert result["system_classification"]
```

---

## Architecture Reference

```
User Photos + Context
        |
        v
[vision_analysis]     3 LLM passes: classify, identify, spatial
        |
        v
[component_lookup]    Fuzzy match against domain DB
        |
        v
[physics_validation]  Domain constraint checks
        |                 |
        | valid           | invalid_fixable (retry up to 2x)
        v                 |---> back to component_lookup
[tradeoff_analyzer]   LLM reasoning about design choices
        |
        v
[alternative_suggester]  LLM proposals + re-validation through physics
        |
        v
[report_generator]    Compile markdown report
```

The graph is defined in `tinker/graph.py` using LangGraph's `StateGraph`. Node functions are in `tinker/nodes/`. The `DomainAdapter` is the only abstraction boundary between the graph and your domain logic — everything domain-specific goes through it.

---

## Checklist

- [ ] Domain directory created under `backend/tinker/domains/`
- [ ] Component DB JSON files with `id`, `type`, `estimated_current_mA`, `estimated_cost_usd`
- [ ] Classification prompt
- [ ] Component identification prompt
- [ ] Spatial estimation prompt
- [ ] Trade-off analysis prompt
- [ ] Alternative suggestions prompt
- [ ] Physics validation with `checks`, `bottlenecks`, `route`
- [ ] `DomainAdapter` subclass with all methods implemented
- [ ] `suggest_alternatives()` returns deterministic suggestions
- [ ] `HeuristicLLMClient` fallback entries for your prompts (for local dev)
- [ ] Integration test passing with `HeuristicLLMClient`
