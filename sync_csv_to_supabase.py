from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path
from typing import Any

from supabase_rest import SupabaseRestClient


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

INCLUDED_POSITIONS = {"국회의원", "국회의장", "국회부의장"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload parsed wealth CSV rows into Supabase.")
    parser.add_argument("--csv-path", default="재산공개_파싱.csv")
    parser.add_argument("--pdf-path", default="")
    parser.add_argument("--source-year", type=int, default=2026)
    parser.add_argument("--label", default="")
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def sha256sum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_numeric(value: str) -> int:
    digits = "".join(ch for ch in str(value) if ch in "0123456789-")
    if not digits or digits == "-":
        return 0
    return int(digits)


def load_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def build_row_hash(row: dict[str, str]) -> str:
    payload = "||".join(str(row.get(column, "")).strip() for column in CSV_COLUMNS)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_batch_payload(args: argparse.Namespace, csv_path: Path, pdf_path: Path | None, rows: list[dict[str, str]]) -> dict[str, Any]:
    lawmaker_rows = sum(1 for row in rows if row.get("직위", "").strip() in INCLUDED_POSITIONS)
    return {
        "source_year": args.source_year,
        "label": args.label or f"{args.source_year} 정기재산공개",
        "source_pdf_name": pdf_path.name if pdf_path else "",
        "source_pdf_sha256": sha256sum(pdf_path) if pdf_path and pdf_path.exists() else "",
        "source_csv_name": csv_path.name,
        "source_csv_sha256": sha256sum(csv_path),
        "record_count": len(rows),
        "lawmaker_record_count": lawmaker_rows,
        "status": "uploading",
        "metadata": {
            "csv_path": str(csv_path),
            "pdf_path": str(pdf_path) if pdf_path else "",
        },
    }


def build_failure_metadata(
    args: argparse.Namespace,
    csv_path: Path,
    pdf_path: Path | None,
    error_message: str,
) -> dict[str, Any]:
    return {
        "csv_path": str(csv_path),
        "pdf_path": str(pdf_path) if pdf_path else "",
        "error": error_message,
    }


def build_officials_payload(batch_id: str, rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    unique_keys: set[tuple[str, str, str]] = set()
    payload: list[dict[str, Any]] = []
    for row in rows:
        name = row.get("성명", "").strip()
        position = row.get("직위", "").strip()
        affiliation = row.get("소속", "").strip()
        if not name:
            continue

        key = (affiliation, position, name)
        if key in unique_keys:
            continue
        unique_keys.add(key)

        payload.append(
            {
                "batch_id": batch_id,
                "affiliation": affiliation,
                "position": position,
                "person_name": name,
                "is_lawmaker": position in INCLUDED_POSITIONS,
            }
        )
    return payload


def build_asset_rows_payload(batch_id: str, rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for row_no, row in enumerate(rows, start=1):
        payload.append(
            {
                "batch_id": batch_id,
                "row_no": row_no,
                "affiliation": row.get("소속", "").strip(),
                "position": row.get("직위", "").strip(),
                "person_name": row.get("성명", "").strip(),
                "relation_name": row.get("본인과의 관계", "").strip(),
                "asset_category": row.get("재산 구분", "").strip(),
                "asset_type": row.get("재산의 종류", "").strip(),
                "asset_description": row.get("소재지 면적 등 권리의 명세", "").strip(),
                "previous_amount_thousand": parse_numeric(row.get("종전가액(천원)", "")),
                "increase_amount_thousand": parse_numeric(row.get("증가액(천원)", "")),
                "decrease_amount_thousand": parse_numeric(row.get("감소액(천원)", "")),
                "current_amount_thousand": parse_numeric(row.get("현재가액(천원)", "")),
                "change_reason": row.get("변동사유", "").strip(),
                "row_hash": build_row_hash(row),
                "is_total_row": row.get("본인과의 관계", "").strip() == "총 계",
            }
        )
    return payload


def chunked(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv_path)
    pdf_path = Path(args.pdf_path) if args.pdf_path else None

    rows = load_csv_rows(csv_path)
    batch_payload = build_batch_payload(args, csv_path, pdf_path, rows)

    print(f"CSV rows: {len(rows):,}")
    print(f"Lawmaker-position rows: {batch_payload['lawmaker_record_count']:,}")
    print(f"CSV sha256: {batch_payload['source_csv_sha256']}")
    if batch_payload["source_pdf_sha256"]:
        print(f"PDF sha256: {batch_payload['source_pdf_sha256']}")

    if args.dry_run:
        print("Dry run only. No data was uploaded.")
        return

    client = SupabaseRestClient.from_env(prefer_service_role=False)

    batch_response = client.insert_rows("import_batches", [batch_payload], returning="representation")
    batch_id = batch_response[0]["id"]
    print(f"Created batch: {batch_id}")
    try:
        officials_payload = build_officials_payload(batch_id, rows)
        officials_chunks = chunked(officials_payload, args.chunk_size)
        for index, chunk in enumerate(officials_chunks, start=1):
            client.insert_rows(
                "officials",
                chunk,
                upsert=True,
                on_conflict="batch_id,affiliation,position,person_name",
                returning="minimal",
            )
            print(f"Uploaded officials chunk {index}/{len(officials_chunks)} ({len(chunk)} rows)")

        asset_rows_payload = build_asset_rows_payload(batch_id, rows)
        asset_chunks = chunked(asset_rows_payload, args.chunk_size)
        for index, chunk in enumerate(asset_chunks, start=1):
            client.insert_rows("asset_rows_raw", chunk, returning="minimal")
            print(f"Uploaded asset chunk {index}/{len(asset_chunks)} ({len(chunk)} rows)")

        client.update_rows(
            "import_batches",
            {
                "status": "completed",
                "record_count": len(rows),
                "lawmaker_record_count": batch_payload["lawmaker_record_count"],
            },
            query={"id": f"eq.{batch_id}"},
            returning="minimal",
        )
        print("Supabase upload completed.")
    except Exception as exc:
        client.update_rows(
            "import_batches",
            {
                "status": "failed",
                "metadata": build_failure_metadata(args, csv_path, pdf_path, str(exc)),
            },
            query={"id": f"eq.{batch_id}"},
            returning="minimal",
        )
        print(f"Supabase upload failed for batch {batch_id}: {exc}")
        raise


if __name__ == "__main__":
    main()
