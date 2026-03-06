# tinker v0.1 Architecture

## Backend

- Domain: `synth_midi`
- Runtime: FastAPI service with background run execution
- Orchestration: graph-shaped sequential pipeline with bounded retry at physics validation
- State persistence: Supabase (`tinker_runs`) when configured, otherwise in-memory fallback

Pipeline order:
1. `vision_analysis`
2. `component_lookup`
3. `physics_validation` (+ retry loop max 2)
4. `tradeoff_analyzer`
5. `alternative_suggester`
6. `report_generator`

## Frontend

- React + Vite
- Notebook-inspired layout from design spec
- Upload + live status polling + staged section rendering

## Data

- Seed JSON data in `backend/tinker/domains/synth_midi/db`
- Fuzzy matching maps visually detected components to spec entries

## Notes

- Anthropic client is implemented for real runs when API key is present.
- Heuristic fallback keeps local development deterministic.
- Supabase is selected automatically when `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set.
