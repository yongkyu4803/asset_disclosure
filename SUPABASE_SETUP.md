# Supabase Setup

## 1. Apply the schema

Run [supabase_schema.sql](/Users/ykpark/2603_재산공개/supabase_schema.sql) in the Supabase SQL editor.

If you want uploads and reads to work with the anon key only, also run
[supabase_anon_policies.sql](/Users/ykpark/2603_재산공개/supabase_anon_policies.sql).

If the tables already exist and you only want the dashboard-oriented indexes, run
[supabase_dashboard_indexes.sql](/Users/ykpark/2603_재산공개/supabase_dashboard_indexes.sql).

## 2. Configure `.env`

Start from [.env.example](/Users/ykpark/2603_재산공개/.env.example) and copy the values into `.env`.

Add the following keys:

```bash
WEALTH_DATA_SOURCE=csv
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-key>
# Optional: pin the app to one batch
WEALTH_BATCH_ID=<uuid>
```

Use `WEALTH_DATA_SOURCE=csv` until the first upload is done. Switch to `supabase` after validation.

## 3. Upload the parsed CSV

```bash
python3 sync_csv_to_supabase.py \
  --csv-path 재산공개_파싱.csv \
  --pdf-path "국회공보 제2026-54호(정기재산공개).pdf" \
  --source-year 2026
```

If you only want to inspect counts and hashes first:

```bash
python3 sync_csv_to_supabase.py --dry-run
```

## 4. Run the app from Supabase

```bash
export WEALTH_DATA_SOURCE=supabase
streamlit run app.py
```

`WEALTH_BATCH_ID` is optional. If omitted, the latest batch in `import_batches` is used.

## 5. Validation targets

After upload, validate these before cutting over:

- `asset_rows_raw`: raw row count should match the CSV row count
- `lawmaker_asset_rows_v` and `lawmaker_totals_v`: totals should match the current CSV-based app outputs
- 국회의원 PDF/CSV spot checks should still come back at 100%
