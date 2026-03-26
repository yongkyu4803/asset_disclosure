grant usage on schema public to anon;

grant select, insert, update on public.import_batches to anon;
grant select, insert on public.officials to anon;
grant select, insert on public.asset_rows_raw to anon;
grant select on public.lawmaker_asset_rows_v to anon;
grant select on public.lawmaker_totals_v to anon;
grant select on public.lawmaker_summary_v to anon;

alter table public.import_batches enable row level security;
alter table public.officials enable row level security;
alter table public.asset_rows_raw enable row level security;

drop policy if exists import_batches_anon_select on public.import_batches;
create policy import_batches_anon_select
on public.import_batches
for select
to anon
using (true);

drop policy if exists import_batches_anon_insert on public.import_batches;
create policy import_batches_anon_insert
on public.import_batches
for insert
to anon
with check (true);

drop policy if exists import_batches_anon_update on public.import_batches;
create policy import_batches_anon_update
on public.import_batches
for update
to anon
using (true)
with check (true);

drop policy if exists officials_anon_select on public.officials;
create policy officials_anon_select
on public.officials
for select
to anon
using (true);

drop policy if exists officials_anon_insert on public.officials;
create policy officials_anon_insert
on public.officials
for insert
to anon
with check (true);

drop policy if exists asset_rows_raw_anon_select on public.asset_rows_raw;
create policy asset_rows_raw_anon_select
on public.asset_rows_raw
for select
to anon
using (true);

drop policy if exists asset_rows_raw_anon_insert on public.asset_rows_raw;
create policy asset_rows_raw_anon_insert
on public.asset_rows_raw
for insert
to anon
with check (true);
