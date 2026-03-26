from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import pandas as pd

from supabase_rest import SupabaseRestClient, get_supabase_config


DEFAULT_CSV_PATH = "재산공개_파싱.csv"
INCLUDED_POSITIONS = ("국회의원", "국회의장", "국회부의장")
NOISE_NAME_PATTERN = "공지사|공개목|공고|공직자윤리법|국회공직자윤리위원"

CSV_COLUMNS = [
    "소속",
    "직위",
    "성명",
    "본인과의 관계",
    "재산 구분",
    "재산의 종류",
    "소재지 면적 등 권리의 명세",
    "종전가액(천원)",
    "증가액(천원)",
    "감소액(천원)",
    "현재가액(천원)",
    "변동사유",
]

TEXT_COLUMNS = [
    "소속",
    "직위",
    "성명",
    "본인과의 관계",
    "재산 구분",
    "재산의 종류",
    "소재지 면적 등 권리의 명세",
    "변동사유",
]

NUMERIC_COLUMNS = [
    "종전가액(천원)",
    "증가액(천원)",
    "감소액(천원)",
    "현재가액(천원)",
]

DB_TO_KR = {
    "affiliation": "소속",
    "position": "직위",
    "person_name": "성명",
    "relation_name": "본인과의 관계",
    "asset_category": "재산 구분",
    "asset_type": "재산의 종류",
    "asset_description": "소재지 면적 등 권리의 명세",
    "previous_amount_thousand": "종전가액(천원)",
    "increase_amount_thousand": "증가액(천원)",
    "decrease_amount_thousand": "감소액(천원)",
    "current_amount_thousand": "현재가액(천원)",
    "change_reason": "변동사유",
}


def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for column in CSV_COLUMNS:
        if column not in result.columns:
            result[column] = ""
    return result[CSV_COLUMNS]


def normalize_raw_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=CSV_COLUMNS)

    result = df.rename(columns=DB_TO_KR)
    result = _ensure_columns(result)

    for column in TEXT_COLUMNS:
        result[column] = result[column].fillna("").astype(str).str.strip()

    for column in NUMERIC_COLUMNS:
        cleaned = result[column].astype(str).str.replace(r"[^\d\-.]", "", regex=True)
        result[column] = pd.to_numeric(cleaned, errors="coerce").fillna(0)

    return result


def clean_public_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    result = normalize_raw_dataframe(df)
    result = result[result["성명"].astype(str).str.strip() != ""].copy()
    result = result[~result["성명"].str.contains(NOISE_NAME_PATTERN, na=False)].copy()
    return result


def filter_positions(df: pd.DataFrame, positions: Iterable[str] = INCLUDED_POSITIONS) -> pd.DataFrame:
    return df[df["직위"].isin(list(positions))].copy()


def load_csv_raw_dataframe(csv_path: str = DEFAULT_CSV_PATH) -> pd.DataFrame:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")
    return normalize_raw_dataframe(pd.read_csv(path))


def _resolve_batch_id(client: SupabaseRestClient, batch_id: str | None = None) -> str:
    resolved = batch_id or os.getenv("WEALTH_BATCH_ID", "").strip()
    if resolved:
        return resolved

    rows = client.select_rows(
        "import_batches",
        query={
            "select": "id,status,created_at",
            "status": "eq.completed",
            "order": "created_at.desc",
        },
        paginate=False,
    )
    if not rows:
        raise RuntimeError("No completed import_batches rows found in Supabase.")
    return rows[0]["id"]


def load_supabase_raw_dataframe(batch_id: str | None = None) -> pd.DataFrame:
    if get_supabase_config() is None:
        raise RuntimeError(
            "Supabase is not configured. Set WEALTH_DATA_SOURCE=csv or provide Supabase credentials."
        )

    client = SupabaseRestClient.from_env()
    resolved_batch_id = _resolve_batch_id(client, batch_id=batch_id)
    rows = client.select_rows(
        "asset_rows_raw",
        query={
            "select": ",".join(
                [
                    "row_no",
                    "affiliation",
                    "position",
                    "person_name",
                    "relation_name",
                    "asset_category",
                    "asset_type",
                    "asset_description",
                    "previous_amount_thousand",
                    "increase_amount_thousand",
                    "decrease_amount_thousand",
                    "current_amount_thousand",
                    "change_reason",
                ]
            ),
            "batch_id": f"eq.{resolved_batch_id}",
            "order": "row_no.asc",
        },
    )
    return normalize_raw_dataframe(pd.DataFrame(rows))


def load_supabase_dashboard_data(batch_id: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    if get_supabase_config() is None:
        raise RuntimeError(
            "Supabase is not configured. Provide Supabase credentials before running the dashboard."
        )

    client = SupabaseRestClient.from_env()
    resolved_batch_id = _resolve_batch_id(client, batch_id=batch_id)

    record_rows = client.select_rows(
        "lawmaker_asset_rows_v",
        query={
            "select": ",".join(
                [
                    "row_no",
                    "affiliation",
                    "position",
                    "person_name",
                    "relation_name",
                    "asset_category",
                    "asset_type",
                    "asset_description",
                    "previous_amount_thousand",
                    "increase_amount_thousand",
                    "decrease_amount_thousand",
                    "current_amount_thousand",
                    "change_reason",
                ]
            ),
            "batch_id": f"eq.{resolved_batch_id}",
            "order": "row_no.asc",
        },
    )
    total_rows = client.select_rows(
        "lawmaker_totals_v",
        query={
            "select": ",".join(
                [
                    "row_no",
                    "affiliation",
                    "position",
                    "person_name",
                    "relation_name",
                    "asset_category",
                    "asset_type",
                    "asset_description",
                    "previous_amount_thousand",
                    "increase_amount_thousand",
                    "decrease_amount_thousand",
                    "current_amount_thousand",
                    "change_reason",
                ]
            ),
            "batch_id": f"eq.{resolved_batch_id}",
            "order": "row_no.asc",
        },
    )

    df_records = normalize_raw_dataframe(pd.DataFrame(record_rows))
    df_totals = normalize_raw_dataframe(pd.DataFrame(total_rows))
    df_totals["순증감액(천원)"] = df_totals["증가액(천원)"] - df_totals["감소액(천원)"]

    return df_records, df_totals


def resolve_data_source(source: str | None = None) -> str:
    resolved = (source or os.getenv("WEALTH_DATA_SOURCE") or "csv").strip().lower()
    if resolved not in {"csv", "supabase"}:
        raise ValueError("WEALTH_DATA_SOURCE must be either 'csv' or 'supabase'.")
    return resolved


def load_raw_dataframe(
    source: str | None = None,
    *,
    csv_path: str = DEFAULT_CSV_PATH,
    batch_id: str | None = None,
) -> pd.DataFrame:
    resolved = resolve_data_source(source)
    if resolved == "supabase":
        return load_supabase_raw_dataframe(batch_id=batch_id)
    return load_csv_raw_dataframe(csv_path=csv_path)


def load_dashboard_data(
    source: str | None = None,
    *,
    csv_path: str = DEFAULT_CSV_PATH,
    batch_id: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    resolved = resolve_data_source(source)
    if resolved == "supabase":
        return load_supabase_dashboard_data(batch_id=batch_id)

    df = load_raw_dataframe(source=resolved, csv_path=csv_path, batch_id=batch_id)
    df = clean_public_dataframe(df)
    df = filter_positions(df)

    df_totals = df[df["본인과의 관계"] == "총 계"].copy()
    df_records = df[df["본인과의 관계"] != "총 계"].copy()
    df_totals["순증감액(천원)"] = df_totals["증가액(천원)"] - df_totals["감소액(천원)"]

    return df_records, df_totals


def load_analysis_records(
    source: str | None = None,
    *,
    csv_path: str = DEFAULT_CSV_PATH,
    batch_id: str | None = None,
) -> pd.DataFrame:
    df_records, _ = load_dashboard_data(source=source, csv_path=csv_path, batch_id=batch_id)
    return df_records
