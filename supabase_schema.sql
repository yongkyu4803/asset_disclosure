create extension if not exists pgcrypto;

create table if not exists public.import_batches (
    id uuid primary key default gen_random_uuid(),
    source_year integer,
    label text not null default '',
    source_pdf_name text not null default '',
    source_pdf_sha256 text not null default '',
    source_csv_name text not null default '',
    source_csv_sha256 text not null default '',
    record_count integer not null default 0,
    lawmaker_record_count integer not null default 0,
    status text not null default 'uploaded' check (status in ('uploaded', 'uploading', 'completed', 'failed')),
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists public.officials (
    id bigint generated always as identity primary key,
    batch_id uuid not null references public.import_batches(id) on delete cascade,
    affiliation text not null default '',
    position text not null default '',
    person_name text not null default '',
    is_lawmaker boolean not null default false,
    created_at timestamptz not null default now(),
    unique (batch_id, affiliation, position, person_name)
);

create table if not exists public.asset_rows_raw (
    id bigint generated always as identity primary key,
    batch_id uuid not null references public.import_batches(id) on delete cascade,
    row_no integer not null,
    affiliation text not null default '',
    position text not null default '',
    person_name text not null default '',
    relation_name text not null default '',
    asset_category text not null default '',
    asset_type text not null default '',
    asset_description text not null default '',
    previous_amount_thousand bigint not null default 0,
    increase_amount_thousand bigint not null default 0,
    decrease_amount_thousand bigint not null default 0,
    current_amount_thousand bigint not null default 0,
    change_reason text not null default '',
    row_hash text not null,
    is_total_row boolean not null default false,
    created_at timestamptz not null default now(),
    unique (batch_id, row_no)
);

create index if not exists idx_import_batches_created_at on public.import_batches (created_at desc);
create index if not exists idx_import_batches_status_created_at on public.import_batches (status, created_at desc);
create index if not exists idx_officials_batch_name on public.officials (batch_id, person_name);
create index if not exists idx_asset_rows_raw_batch_row_no on public.asset_rows_raw (batch_id, row_no);
create index if not exists idx_asset_rows_raw_batch_person on public.asset_rows_raw (batch_id, person_name);
create index if not exists idx_asset_rows_raw_batch_position on public.asset_rows_raw (batch_id, position);
create index if not exists idx_asset_rows_raw_batch_total on public.asset_rows_raw (batch_id, is_total_row);
create index if not exists idx_asset_rows_raw_dashboard_records
on public.asset_rows_raw (batch_id, row_no)
where position in ('국회의원', '국회의장', '국회부의장') and is_total_row = false;
create index if not exists idx_asset_rows_raw_dashboard_totals
on public.asset_rows_raw (batch_id, row_no)
where position in ('국회의원', '국회의장', '국회부의장') and is_total_row = true;
create index if not exists idx_asset_rows_raw_dashboard_person
on public.asset_rows_raw (batch_id, person_name, row_no)
where position in ('국회의원', '국회의장', '국회부의장');

create or replace view public.lawmaker_asset_rows_v as
select
    r.*
from public.asset_rows_raw r
where r.position in ('국회의원', '국회의장', '국회부의장')
  and r.is_total_row = false;

create or replace view public.lawmaker_totals_v as
select
    r.*
from public.asset_rows_raw r
where r.position in ('국회의원', '국회의장', '국회부의장')
  and r.is_total_row = true;

create or replace view public.lawmaker_summary_v as
select
    r.batch_id,
    r.affiliation,
    r.position,
    r.person_name,
    max(case when r.is_total_row then r.previous_amount_thousand end) as total_previous_amount_thousand,
    max(case when r.is_total_row then r.increase_amount_thousand end) as total_increase_amount_thousand,
    max(case when r.is_total_row then r.decrease_amount_thousand end) as total_decrease_amount_thousand,
    max(case when r.is_total_row then r.current_amount_thousand end) as total_current_amount_thousand,
    count(*) filter (where r.is_total_row = false) as asset_record_count
from public.asset_rows_raw r
where r.position in ('국회의원', '국회의장', '국회부의장')
group by r.batch_id, r.affiliation, r.position, r.person_name;
