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

# Filter 국회의원 + 의장 + 부의장 (exclude 전문위원, 사무총장 etc.)
df = df[df['직위'].isin(['국회의원', '국회의장', '국회부의장'])].copy()

print("CSV 파일 생성 중...")

# 1. 수도권 아파트 보유 현황 (본인+배우자)
print("1. 수도권 아파트...")
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
capital_apts['총가액(원)'] = capital_apts['총가액(천원)'] * 1000
capital_apts = capital_apts.sort_values('아파트수', ascending=False).head(10)
capital_apts.to_csv('분석1_수도권아파트.csv', index=False, encoding='utf-8-sig')

# 2. 주식 보유 현황
print("2. 주식 포트폴리오...")
stock_df = df[df['재산 구분'] == '증권'].copy()

def extract_stock_names(text):
    if pd.isna(text):
        return []
    text = str(text)
    names = []
    parts = text.split(',')
    for part in parts:
        part = part.strip()
        match = re.match(r'^([가-힣A-Za-z0-9&\(\)]+)\s+[\d\.]+주', part)
        if match:
            company_name = match.group(1).strip()
            if company_name and len(company_name) > 1:
                names.append(company_name)
    return names

stock_df['회사명들'] = stock_df['소재지 면적 등 권리의 명세'].apply(extract_stock_names)

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
    stock_results = []
    for company, count in stock_counter.most_common(15):
        holders = set(s['의원'] for s in all_stocks if s['회사명'] == company)
        stock_results.append({
            '회사명': company,
            '보유건수': count,
            '보유인원': len(holders)
        })
    pd.DataFrame(stock_results).to_csv('분석2_주식포트폴리오.csv', index=False, encoding='utf-8-sig')

# 3. 차량 3대 이상 보유
print("3. 차량 3대 이상 보유...")
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

multi_car_results = []
if not car_count_df.empty:
    for idx, row in car_count_df.iterrows():
        total_value = row['총가액(천원)'] * 1000
        multi_car_results.append({
            '성명': row['성명'],
            '총대수': int(row['총대수']),
            '총가액(원)': int(total_value)
        })

pd.DataFrame(multi_car_results).to_csv('분석3_다차량보유.csv', index=False, encoding='utf-8-sig')

# 4. 예금왕
print("4. 예금왕...")
deposit_df = df[df['재산 구분'] == '예금'].groupby('성명')['현재가액(천원)'].sum().reset_index()
deposit_df.columns = ['성명', '예금액(천원)']
deposit_df['예금액(원)'] = deposit_df['예금액(천원)'] * 1000
deposit_df = deposit_df.sort_values('예금액(천원)', ascending=False).head(10)
deposit_df.to_csv('분석4_예금왕.csv', index=False, encoding='utf-8-sig')

# 5. 토지왕
print("5. 토지왕...")
land_df = df[df['재산 구분'] == '토지'].groupby('성명').agg({
    '현재가액(천원)': ['count', 'sum']
}).reset_index()
land_df.columns = ['성명', '토지필지수', '총가액(천원)']
land_df['총가액(원)'] = land_df['총가액(천원)'] * 1000
land_df = land_df.sort_values('총가액(천원)', ascending=False).head(10)
land_df.to_csv('분석5_토지왕.csv', index=False, encoding='utf-8-sig')

# 6. 채무
print("6. 채무...")
debt_df = df[df['재산 구분'].str.contains('채무', na=False)].groupby('성명')['현재가액(천원)'].sum().reset_index()
debt_df.columns = ['성명', '채무액(천원)']
debt_df['채무액(원)'] = debt_df['채무액(천원)'] * 1000
debt_df = debt_df.sort_values('채무액(천원)', ascending=False).head(10)
debt_df.to_csv('분석6_채무.csv', index=False, encoding='utf-8-sig')

# 7. 본인 vs 배우자
print("7. 본인 vs 배우자...")
person_assets = df[df['본인과의 관계'] == '본인'].groupby('성명')['현재가액(천원)'].sum().reset_index()
person_assets.columns = ['성명', '본인재산(천원)']

spouse_assets = df[df['본인과의 관계'] == '배우자'].groupby('성명')['현재가액(천원)'].sum().reset_index()
spouse_assets.columns = ['성명', '배우자재산(천원)']

comparison = person_assets.merge(spouse_assets, on='성명', how='outer').fillna(0)
comparison['본인재산(원)'] = comparison['본인재산(천원)'] * 1000
comparison['배우자재산(원)'] = comparison['배우자재산(천원)'] * 1000
comparison['총재산(천원)'] = comparison['본인재산(천원)'] + comparison['배우자재산(천원)']
comparison['총재산(원)'] = comparison['총재산(천원)'] * 1000
comparison['배우자비율(%)'] = (comparison['배우자재산(천원)'] / comparison['총재산(천원)'] * 100).round(1)

spouse_rich = comparison[comparison['배우자재산(천원)'] > comparison['본인재산(천원)']].sort_values('배우자비율(%)', ascending=False).head(10)
spouse_rich[['성명', '본인재산(원)', '배우자재산(원)', '총재산(원)', '배우자비율(%)']].to_csv('분석7_배우자재산비교.csv', index=False, encoding='utf-8-sig')

# 8. 해외 자산
print("8. 해외 자산...")
foreign_patterns = [
    r'(미국|캐나다|호주|영국|프랑스|독일|일본|중국|싱가포르|홍콩)\s+([\w]+(?:주|도|성|현|시))',
    r'\(미국\)|\(캐나다\)|\(호주\)|\(영국\)|\(일본\)|\(중국\)',
    r'[A-Z][a-z]+\s+of\s+[A-Z]',
]

foreign_assets = []
for idx, row in df.iterrows():
    if row['현재가액(천원)'] <= 0:
        continue

    location = str(row['소재지 면적 등 권리의 명세'])

    if '은행' in location and not any(re.search(pattern, location) for pattern in foreign_patterns):
        continue

    is_foreign = any(re.search(pattern, location) for pattern in foreign_patterns)

    if is_foreign:
        foreign_assets.append({
            '성명': row['성명'],
            '재산구분': row['재산 구분'],
            '재산종류': row['재산의 종류'],
            '가액(천원)': row['현재가액(천원)'],
            '위치': location
        })

if foreign_assets:
    foreign_by_person = {}
    for asset in foreign_assets:
        name = asset['성명']
        if name not in foreign_by_person:
            foreign_by_person[name] = {'건수': 0, '총가액(천원)': 0}
        foreign_by_person[name]['건수'] += 1
        foreign_by_person[name]['총가액(천원)'] += asset['가액(천원)']

    sorted_foreign = sorted(foreign_by_person.items(), key=lambda x: x[1]['총가액(천원)'], reverse=True)[:10]
    foreign_results = []
    for name, data in sorted_foreign:
        foreign_results.append({
            '성명': name,
            '건수': data['건수'],
            '총가액(천원)': data['총가액(천원)'],
            '총가액(원)': data['총가액(천원)'] * 1000
        })
    pd.DataFrame(foreign_results).to_csv('분석8_해외자산.csv', index=False, encoding='utf-8-sig')

# 9. 보험왕
print("9. 보험왕...")
insurance_keywords = ['생명보험', '손해보험', '화재보험']
insurance_df = df[df['재산 구분'] == '예금'].copy()

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
    insurance_results = []
    for name, amount in sorted_insurance:
        insurance_results.append({
            '성명': name,
            '보험액(천원)': amount,
            '보험액(원)': amount * 1000
        })
    pd.DataFrame(insurance_results).to_csv('분석9_보험왕.csv', index=False, encoding='utf-8-sig')

print("\n" + "="*80)
print("✅ CSV 파일 생성 완료!")
print("="*80)
print("\n생성된 파일 목록:")
print("  - 분석1_수도권아파트.csv")
print("  - 분석2_주식포트폴리오.csv")
print("  - 분석3_다차량보유.csv")
print("  - 분석4_예금왕.csv")
print("  - 분석5_토지왕.csv")
print("  - 분석6_채무.csv")
print("  - 분석7_배우자재산비교.csv")
print("  - 분석8_해외자산.csv")
print("  - 분석9_보험왕.csv")
print("="*80)
