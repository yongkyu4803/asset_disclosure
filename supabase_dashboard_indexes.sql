create index if not exists idx_import_batches_status_created_at
on public.import_batches (status, created_at desc);

create index if not exists idx_asset_rows_raw_dashboard_records
on public.asset_rows_raw (batch_id, row_no)
where position in ('국회의원', '국회의장', '국회부의장') and is_total_row = false;

create index if not exists idx_asset_rows_raw_dashboard_totals
on public.asset_rows_raw (batch_id, row_no)
where position in ('국회의원', '국회의장', '국회부의장') and is_total_row = true;

create index if not exists idx_asset_rows_raw_dashboard_person
on public.asset_rows_raw (batch_id, person_name, row_no)
where position in ('국회의원', '국회의장', '국회부의장');
