import pandas as pd
import re
from collections import Counter

# Load data
df = pd.read_csv("재산공개_파싱.csv")

# Clean numeric columns
numeric_cols = ["종전가액(천원)", "증가액(천원)", "감소액(천원)", "현재가액(천원)"]
for col in numeric_cols:
    df[col] = df[col].astype(str).str.replace(r'[^\d\-.]', '', regex=True)
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# Remove rows without names and header rows
df = df[df['성명'].notna()]
df = df[df['본인과의 관계'] != '총 계']
df = df[~df['성명'].str.contains('공지사|공개목|공고|공직자윤리법|국회공직자윤리위원', na=False)]

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
print("🚗 3. 자동차 애호가 (외제차 또는 3대 이상 보유)")
print("="*80)

# Filter cars
car_df = df[df['재산의 종류'] == '자동차'].copy()

# Define luxury/import car brands (관용차 제외)
luxury_brands = ['벤츠', 'BMW', '아우디', '포르쉐', '테슬라', '렉서스', '볼보',
                 'Benz', 'Porsche', 'Audi', 'Lexus', 'Tesla', 'Mercedes',
                 '람보르기니', '페라리', '맥라렌', '벤틀리', '롤스로이스',
                 '마세라티', '애스턴마틴', '재규어', '랜드로버']

# 1. 외제차 보유자
luxury_car_df = car_df[car_df['소재지 면적 등 권리의 명세'].apply(
    lambda x: any(brand in str(x) for brand in luxury_brands) if pd.notna(x) else False
)].copy()

print("\n🏎️ 외제차 보유 TOP 10:")
if not luxury_car_df.empty:
    luxury_owners = luxury_car_df.groupby('성명').agg({
        '현재가액(천원)': 'count'
    }).reset_index()
    luxury_owners.columns = ['성명', '대수']
    luxury_owners = luxury_owners.sort_values('대수', ascending=False).head(10)

    for idx, row in luxury_owners.iterrows():
        cars_detail = luxury_car_df[luxury_car_df['성명'] == row['성명']]['소재지 면적 등 권리의 명세'].tolist()
        car_brands = []
        for car in cars_detail:
            for brand in luxury_brands:
                if brand in str(car):
                    # Extract more detail
                    car_brands.append(brand)
                    break
        print(f"  {row['성명']}: {int(row['대수'])}대 ({', '.join(set(car_brands))})")
else:
    print("  데이터 없음")

# 2. 차량 3대 이상 보유자 (총 보유 대수 기준)
print("\n🚙 차량 3대 이상 보유 TOP 10:")
car_count_df = car_df.groupby('성명').size().reset_index(name='총대수')
car_count_df = car_count_df[car_count_df['총대수'] >= 3].sort_values('총대수', ascending=False).head(10)

if not car_count_df.empty:
    for idx, row in car_count_df.iterrows():
        total_value = car_df[car_df['성명'] == row['성명']]['현재가액(천원)'].sum() * 1000
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

# Find foreign assets
foreign_keywords = ['미국', '캐나다', '호주', '유럽', '중국', '일본', '베트남', '싱가포르', '홍콩', '영국', '프랑스', '독일']
foreign_assets = []

for idx, row in df.iterrows():
    location = str(row['소재지 면적 등 권리의 명세'])
    if any(keyword in location for keyword in foreign_keywords):
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
print("  3. 자동차 애호가 (외제차 & 3대 이상 보유자)")
print("  4. 예금왕 TOP 10 (현금 부자)")
print("  5. 토지왕 TOP 10")
print("  6. 채무 TOP 10")
print("  7. 본인 vs 배우자 재산 비교 TOP 10")
print("  8. 해외 자산 보유 TOP 10")
print("  9. 보험왕 TOP 10")
print("="*80)
