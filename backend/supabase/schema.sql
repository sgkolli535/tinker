-- tinker run persistence table
create table if not exists public.tinker_runs (
  run_id text primary key,
  status text not null,
  current_node text,
  retry_count integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  state jsonb not null default '{}'::jsonb,
  trace jsonb not null default '[]'::jsonb
);

create index if not exists tinker_runs_status_idx on public.tinker_runs (status);
create index if not exists tinker_runs_updated_at_idx on public.tinker_runs (updated_at desc);

-- Optional if you enable RLS for this table and still use service role key from backend.
alter table public.tinker_runs enable row level security;

-- Service-role only policy (safe default for backend-only access).
drop policy if exists "service_role_all_tinker_runs" on public.tinker_runs;
create policy "service_role_all_tinker_runs"
on public.tinker_runs
for all
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');
