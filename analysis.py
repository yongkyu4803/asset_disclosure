import pandas as pd
import re
from collections import Counter

from wealth_data import load_analysis_records

# Load data
df = load_analysis_records()

print("="*80)
print("🏠 1. 수도권 아파트 보유 현황 (본인+배우자)")
print("="*80)

# Filter apartments in capital area (본인+배우자)
apt_df = df[(df['재산의 종류'] == '아파트') &
            (df['본인과의 관계'].isin(['본인', '배우자']))].copy()
capital_keywords = ['서울', '경기', '인천']
apt_df['is_capital'] = apt_df['소재지 면적 등 권리의 명세'].apply(
    lambda x: any(kw in str(x) for kw in capital_keywords) if pd.notna(x) else False
)

capital_apts = apt_df[apt_df['is_capital']].groupby('성명').agg({
    '현재가액(천원)': ['count', 'sum']
}).reset_index()
capital_apts.columns = ['성명', '아파트수', '총가액(천원)']
capital_apts = capital_apts.sort_values('아파트수', ascending=False).head(10)

print("\n수도권 아파트 보유 TOP 10 (본인+배우자):")
for idx, row in capital_apts.iterrows():
    total_value = row['총가액(천원)'] * 1000
    uk = total_value // 100000000
    man = (total_value % 100000000) // 10000
    value_str = f"{uk:,.0f}억 {man:,.0f}만원" if uk > 0 else f"{man:,.0f}만원"
    print(f"  {row['성명']}: {int(row['아파트수'])}채 (총 {value_str})")

print("\n" + "="*80)
print("💼 2. 주식 보유 현황")
print("="*80)

# Filter stocks - 증권 재산 구분 중 상장주식, 비상장주식
stock_df = df[df['재산 구분'] == '증권'].copy()

# Extract stock names from 소재지 면적 등 권리의 명세
def extract_stock_names(text):
    if pd.isna(text):
        return []

    text = str(text)
    names = []

    # Split by comma and extract company names
    parts = text.split(',')
    for part in parts:
        part = part.strip()
        # Extract pattern: "회사명 숫자주"
        match = re.match(r'^([가-힣A-Za-z0-9&\(\)]+)\s+[\d\.]+주', part)
        if match:
            company_name = match.group(1).strip()
            # Filter out common non-company words
            if company_name and len(company_name) > 1:
                names.append(company_name)

    return names

stock_df['회사명들'] = stock_df['소재지 면적 등 권리의 명세'].apply(extract_stock_names)

# Flatten all stock names with member info
all_stocks = []
for idx, row in stock_df.iterrows():
    for company in row['회사명들']:
        all_stocks.append({
            '회사명': company,
            '가액': row['현재가액(천원)'],
            '의원': row['성명']
        })

if all_stocks:
    stock_counter = Counter([s['회사명'] for s in all_stocks])
    print("\n국회의원들이 많이 보유한 주식 TOP 15 (보유 건수 기준):")
    for company, count in stock_counter.most_common(15):
        # Find unique members holding this stock
        holders = set(s['의원'] for s in all_stocks if s['회사명'] == company)
        print(f"  {company}: {count}건 ({len(holders)}명 보유)")
else:
    print("\n주식 데이터가 없습니다.")

print("\n" + "="*80)
print("🚗 3. 차량 3대 이상 보유")
print("="*80)

# Filter cars (현재가액 > 0인 것만)
car_df = df[df['재산의 종류'] == '자동차'].copy()
car_df = car_df[car_df['현재가액(천원)'] > 0].copy()

# 차량 식별 정보 추출 (연식+차종+배기량으로 고유 차량 식별)
def extract_car_id(text):
    if pd.isna(text):
        return None
    text = str(text)
    year_match = re.search(r'(\d{4})년식', text)
    year = year_match.group(1) if year_match else "unknown"
    model_match = re.search(r'년식\s+([^\s]+)', text)
    model = model_match.group(1) if model_match else "unknown"
    cc_match = re.search(r'배기량\(([0-9,]+)cc\)', text)
    cc = cc_match.group(1).replace(',', '') if cc_match else "unknown"
    return f"{year}_{model}_{cc}"

car_df['차량ID'] = car_df['소재지 면적 등 권리의 명세'].apply(extract_car_id)

# 사람별 고유 차량 개수 카운트
car_counts = []
for name in car_df['성명'].unique():
    person_cars = car_df[car_df['성명'] == name]
    unique_cars = person_cars['차량ID'].nunique()
    total_value = person_cars['현재가액(천원)'].sum()
    car_counts.append({
        '성명': name,
        '총대수': unique_cars,
        '총가액(천원)': total_value
    })

car_count_df = pd.DataFrame(car_counts)
car_count_df = car_count_df[car_count_df['총대수'] >= 3].sort_values('총대수', ascending=False).head(10)

print("\n🚙 차량 3대 이상 보유 TOP 10:")
if not car_count_df.empty:
    for idx, row in car_count_df.iterrows():
        total_value = row['총가액(천원)'] * 1000
        uk = int(total_value // 100000000)
        man = int((total_value % 100000000) // 10000)
        value_str = f"{uk:,}억 {man:,}만원" if uk > 0 else f"{man:,}만원"
        print(f"  {row['성명']}: {int(row['총대수'])}대 (총 {value_str})")
else:
    print("  데이터 없음")

print("\n" + "="*80)
print("💰 4. 예금왕 (현금 부자)")
print("="*80)

# Calculate total deposits per person
deposit_df = df[df['재산 구분'] == '예금'].groupby('성명')['현재가액(천원)'].sum().reset_index()
deposit_df = deposit_df.sort_values('현재가액(천원)', ascending=False).head(10)

print("\n예금 보유액 TOP 10:")
for idx, row in deposit_df.iterrows():
    total_value = row['현재가액(천원)'] * 1000
    uk = total_value // 100000000
    man = (total_value % 100000000) // 10000
    value_str = f"{uk:,.0f}억 {man:,.0f}만원" if uk > 0 else f"{man:,.0f}만원"
    print(f"  {row['성명']}: {value_str}")

print("\n" + "="*80)
print("📊 5. 토지 보유 현황")
print("="*80)

# Calculate total land per person
land_df = df[df['재산 구분'] == '토지'].groupby('성명').agg({
    '현재가액(천원)': ['count', 'sum']
}).reset_index()
land_df.columns = ['성명', '토지필지수', '총가액(천원)']
land_df = land_df.sort_values('총가액(천원)', ascending=False).head(10)

print("\n토지 보유 가액 TOP 10:")
for idx, row in land_df.iterrows():
    total_value = row['총가액(천원)'] * 1000
    uk = total_value // 100000000
    man = (total_value % 100000000) // 10000
    value_str = f"{uk:,.0f}억 {man:,.0f}만원" if uk > 0 else f"{man:,.0f}만원"
    print(f"  {row['성명']}: {int(row['토지필지수'])}필지 (총 {value_str})")

print("\n" + "="*80)
print("💳 6. 채무 현황")
print("="*80)

# Calculate total debt per person
debt_df = df[df['재산 구분'].str.contains('채무', na=False)].groupby('성명')['현재가액(천원)'].sum().reset_index()
debt_df = debt_df.sort_values('현재가액(천원)', ascending=False).head(10)

print("\n채무 보유액 TOP 10:")
for idx, row in debt_df.iterrows():
    total_value = row['현재가액(천원)'] * 1000
    uk = total_value // 100000000
    man = (total_value % 100000000) // 10000
    value_str = f"{uk:,.0f}억 {man:,.0f}만원" if uk > 0 else f"{man:,.0f}만원"
    print(f"  {row['성명']}: {value_str}")

print("\n" + "="*80)
print("👨‍👩‍👧‍👦 7. 본인 vs 배우자 재산 비교 (총액 기준)")
print("="*80)

# Compare assets between 본인 and 배우자
person_assets = df[df['본인과의 관계'] == '본인'].groupby('성명')['현재가액(천원)'].sum().reset_index()
person_assets.columns = ['성명', '본인재산']

spouse_assets = df[df['본인과의 관계'] == '배우자'].groupby('성명')['현재가액(천원)'].sum().reset_index()
spouse_assets.columns = ['성명', '배우자재산']

# Merge
comparison = person_assets.merge(spouse_assets, on='성명', how='outer').fillna(0)
comparison['총재산'] = comparison['본인재산'] + comparison['배우자재산']
comparison['배우자비율'] = (comparison['배우자재산'] / comparison['총재산'] * 100).round(1)

# Top spouse ratio (where spouse has more)
spouse_rich = comparison[comparison['배우자재산'] > comparison['본인재산']].sort_values('배우자비율', ascending=False).head(10)

if not spouse_rich.empty:
    print("\n배우자 재산이 더 많은 경우 TOP 10:")
    for idx, row in spouse_rich.iterrows():
        spouse_val = row['배우자재산'] * 1000
        uk = int(spouse_val // 100000000)
        man = int((spouse_val % 100000000) // 10000)
        value_str = f"{uk:,}억 {man:,}만원" if uk > 0 else f"{man:,}만원"
        print(f"  {row['성명']}: 배우자 {value_str} ({row['배우자비율']:.1f}%)")

print("\n" + "="*80)
print("🌍 8. 해외 자산 보유 현황")
print("="*80)

# Find foreign assets with improved pattern matching
foreign_patterns = [
    r'(미국|캐나다|호주|영국|프랑스|독일|일본|중국|싱가포르|홍콩)\s+([\w]+(?:주|도|성|현|시))',
    r'\(미국\)|\(캐나다\)|\(호주\)|\(영국\)|\(일본\)|\(중국\)',
    r'[A-Z][a-z]+\s+of\s+[A-Z]',  # Bank of America 패턴
]

foreign_assets = []
for idx, row in df.iterrows():
    if row['현재가액(천원)'] <= 0:  # 현재가액이 0 이하인 것 제외
        continue

    location = str(row['소재지 면적 등 권리의 명세'])

    # 은행명 오검출 제외 (예: 중국은행, 미국국채 등)
    if '은행' in location and not any(re.search(pattern, location) for pattern in foreign_patterns):
        continue

    # 패턴 매칭
    is_foreign = any(re.search(pattern, location) for pattern in foreign_patterns)

    if is_foreign:
        foreign_assets.append({
            '성명': row['성명'],
            '재산구분': row['재산 구분'],
            '재산종류': row['재산의 종류'],
            '가액': row['현재가액(천원)'],
            '위치': location[:50] + '...' if len(location) > 50 else location
        })

if foreign_assets:
    # Group by person
    foreign_by_person = {}
    for asset in foreign_assets:
        name = asset['성명']
        if name not in foreign_by_person:
            foreign_by_person[name] = {'건수': 0, '총가액': 0}
        foreign_by_person[name]['건수'] += 1
        foreign_by_person[name]['총가액'] += asset['가액']

    # Sort by total value
    sorted_foreign = sorted(foreign_by_person.items(), key=lambda x: x[1]['총가액'], reverse=True)[:10]

    print("\n해외 자산 보유 TOP 10:")
    for name, data in sorted_foreign:
        total_value = data['총가액'] * 1000
        uk = int(total_value // 100000000)
        man = int((total_value % 100000000) // 10000)
        value_str = f"{uk:,}억 {man:,}만원" if uk > 0 else f"{man:,}만원"
        print(f"  {name}: {data['건수']}건 (총 {value_str})")
else:
    print("\n해외 자산 데이터가 없습니다.")

print("\n" + "="*80)
print("💎 9. 보험왕 (보험 보유액)")
print("="*80)

# Find insurance assets in 예금 (보험상품들이 예금에 포함되어 있음)
insurance_keywords = ['생명보험', '손해보험', '화재보험']
insurance_df = df[df['재산 구분'] == '예금'].copy()

# Calculate insurance amounts per person
insurance_by_person = {}
for idx, row in insurance_df.iterrows():
    description = str(row['소재지 면적 등 권리의 명세'])
    if any(keyword in description for keyword in insurance_keywords):
        name = row['성명']
        if name not in insurance_by_person:
            insurance_by_person[name] = 0
        insurance_by_person[name] += row['현재가액(천원)']

if insurance_by_person:
    sorted_insurance = sorted(insurance_by_person.items(), key=lambda x: x[1], reverse=True)[:10]
    print("\n보험 상품 보유액 추정 TOP 10:")
    for name, amount in sorted_insurance:
        total_value = amount * 1000
        uk = int(total_value // 100000000)
        man = int((total_value % 100000000) // 10000)
        value_str = f"{uk:,}억 {man:,}만원" if uk > 0 else f"{man:,}만원"
        print(f"  {name}: {value_str}")
else:
    print("\n보험 상품 데이터가 없습니다.")

print("\n" + "="*80)
print("🎯 분석 완료!")
print("="*80)
print("\n총 분석 항목:")
print("  1. 수도권 아파트 보유 현황 (본인+배우자)")
print("  2. 주식 포트폴리오 TOP 15 (삼성전자, 엔비디아, 테슬라 등)")
print("  3. 차량 3대 이상 보유자 TOP 10")
print("  4. 예금왕 TOP 10 (현금 부자)")
print("  5. 토지왕 TOP 10")
print("  6. 채무 TOP 10")
print("  7. 본인 vs 배우자 재산 비교 TOP 10")
print("  8. 해외 자산 보유 TOP 10")
print("  9. 보험왕 TOP 10")
print("="*80)
