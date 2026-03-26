import pdfplumber
import csv
import re

pdf_path = "/Users/ykpark/2603_재산공개/국회공보 제2026-54호(정기재산공개).pdf"
csv_path = "/Users/ykpark/2603_재산공개/재산공개_파싱.csv"

def clean_text(text):
    if text is None:
        return ""
    # Replace newlines with spaces and strip extra spaces
    return " ".join(str(text).split())

def is_category_row(row):
    # Category rows typically start with `▶`
    text = clean_text(row[0])
    return text.startswith("▶")

def is_header_row(row):
    # If the row has metadata or titles (e.g. 본인과의 관계, (단위 : 천원))
    text0 = clean_text(row[0])
    if "본인과의" in text0 or "단위" in text0 or "공지사항" in text0:
        return True
    return False

def extract_person_info(row):
    # Looks for: `['소속', '국회', None, '직위', '국회의장', None, '성명', '우원식']`
    # Or variations of it in the row.
    cleaned_row = [clean_text(cell) for cell in row]
    if "소속" in cleaned_row and "직위" in cleaned_row and "성명" in cleaned_row:
        try:
            sosok_idx = cleaned_row.index("소속")
            jikwi_idx = cleaned_row.index("직위")
            name_idx = cleaned_row.index("성명")
            
            sosok = cleaned_row[sosok_idx + 1] if sosok_idx + 1 < len(cleaned_row) else ""
            jikwi = cleaned_row[jikwi_idx + 1] if jikwi_idx + 1 < len(cleaned_row) else ""
            name = cleaned_row[name_idx + 1] if name_idx + 1 < len(cleaned_row) else ""
            return sosok, jikwi, name
        except Exception:
            return None
    return None

def main():
    current_sosok = ""
    current_jikwi = ""
    current_name = ""
    current_category = ""

    parsed_data = []
    
    headers = [
        "소속", "직위", "성명", "본인과의 관계", "재산 구분", "재산의 종류", 
        "소재지 면적 등 권리의 명세", "종전가액(천원)", "증가액(천원)", 
        "감소액(천원)", "현재가액(천원)", "변동사유"
    ]

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            if i % 10 == 0:
                print(f"Processing page {i+1}/{total_pages}...")
                
            tables = page.extract_tables()
            if not tables:
                continue
                
            for table in tables:
                for row in table:
                    # Pad row if too short
                    if len(row) < 8:
                        row.extend([None] * (8 - len(row)))

                    person_info = extract_person_info(row)
                    if person_info:
                        current_sosok, current_jikwi, current_name = person_info
                        current_category = ""
                        continue

                    if is_header_row(row):
                        continue

                    if is_category_row(row):
                        cat_text = clean_text(row[0]).replace("▶", "").strip()
                        cat_text = cat_text.replace("(소계)", "").strip()
                        current_category = cat_text
                        continue

                    # Data row
                    # 0: 본인과의 관계, 1: 재산의 종류, 2: 소재지 면적 등, 
                    # 3: 종전가액, 4: 증가액, 5: 감소액, 6: 현재가액, 7: 변동사유
                    관계 = clean_text(row[0])
                    종류 = clean_text(row[1])
                    명세 = clean_text(row[2])
                    종전 = clean_text(row[3])
                    증가 = clean_text(row[4])
                    감소 = clean_text(row[5])
                    현재 = clean_text(row[6])
                    사유 = clean_text(row[7])

                    if not 관계 and not 종류 and not 명세:
                        continue # Empty row
                    
                    parsed_data.append([
                        current_sosok, current_jikwi, current_name,
                        관계, current_category, 종류, 명세, 종전, 증가, 감소, 현재, 사유
                    ])

    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(parsed_data)
        
    print(f"Parsing complete. {len(parsed_data)} records saved to {csv_path}")

if __name__ == "__main__":
    main()
