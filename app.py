import streamlit as st
import pandas as pd
import plotly.express as px
import re
from collections import Counter

st.set_page_config(page_title="국회의원 재산공개 대시보드", layout="wide")

@st.cache_data
def load_data():
    csv_path = "재산공개_파싱.csv"
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame()

    # Clean numeric columns
    numeric_cols = ["종전가액(천원)", "증가액(천원)", "감소액(천원)", "현재가액(천원)"]
    for col in numeric_cols:
        df[col] = df[col].astype(str).str.replace(r'[^\d\-.]', '', regex=True)
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Remove empty names and header rows
    df = df[df['성명'].notna()]
    df = df[~df['성명'].str.contains('공지사|공개목|공고|공직자윤리법|국회공직자윤리위원', na=False)]

    # Filter 국회의원 + 의장 + 부의장 (exclude 전문위원, 사무총장 etc.)
    df = df[df['직위'].isin(['국회의원', '국회의장', '국회부의장'])].copy()

    # Separate the '총 계' (Total) rows from the detailed records
    df_totals = df[df['본인과의 관계'] == '총 계'].copy()
    df_records = df[df['본인과의 관계'] != '총 계'].copy()

    # Calculate net increase/decrease
    df_totals['순증감액(천원)'] = df_totals['증가액(천원)'] - df_totals['감소액(천원)']

    return df_records, df_totals

df_records, df_totals = load_data()

if df_records.empty or df_totals.empty:
    st.error("데이터를 불러오지 못했습니다. CSV 파일 경로와 상태를 확인해주세요.")
    st.stop()

st.sidebar.title("📊 메뉴")
menu = st.sidebar.radio("이동", [
    "전체 통계 및 순위",
    "💼 주식 포트폴리오",
    "🚗 자동차 분석",
    "🏠 부동산 분석",
    "👫 배우자 재산 비교",
    "🌍 해외 자산",
    "국회의원별 상세 조회"
])

def format_currency(val):
    return f"{val*1000:,.0f}원"

def format_korean_currency(val_in_thousands):
    val = int(val_in_thousands) * 1000
    if val == 0:
        return "0원"

    is_negative = val < 0
    val = abs(val)

    uk = val // 100000000
    man = (val % 100000000) // 10000

    parts = []
    if uk > 0:
        parts.append(f"{uk:,.0f}억")
    if man > 0:
        parts.append(f"{man:,.0f}만")

    if not parts:
        return f"{val:,}원"

    result = " ".join(parts) + "원"
    return "-" + result if is_negative else result

if menu == "전체 통계 및 순위":
    st.title("🏛️ 국회의원 재산 전체 통계 및 순위")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💰 재산 총액 Top 10")
        top10_wealth = df_totals.sort_values("현재가액(천원)", ascending=False).head(10)
        fig1 = px.bar(top10_wealth, x="성명", y="현재가액(천원)",
                      text="현재가액(천원)", color="현재가액(천원)", color_continuous_scale="Blues")
        fig1.update_traces(texttemplate='%{text:,.0f}천원', textposition='outside')
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("💵 예금 보유액 Top 10")
        deposit_df = df_records[df_records['재산 구분'] == '예금'].groupby('성명')['현재가액(천원)'].sum().reset_index()
        deposit_df = deposit_df.sort_values('현재가액(천원)', ascending=False).head(10)
        fig2 = px.bar(deposit_df, x="성명", y="현재가액(천원)",
                      text="현재가액(천원)", color="현재가액(천원)", color_continuous_scale="Greens")
        fig2.update_traces(texttemplate='%{text:,.0f}천원', textposition='outside')
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    col3, col4 = st.columns(2)

    with col3:
        st.subheader("🏞️ 토지 보유액 Top 10")
        land_df = df_records[df_records['재산 구분'] == '토지'].groupby('성명').agg({
            '현재가액(천원)': 'sum'
        }).reset_index()
        land_df = land_df.sort_values('현재가액(천원)', ascending=False).head(10)
        fig3 = px.bar(land_df, x="성명", y="현재가액(천원)",
                      text="현재가액(천원)", color="현재가액(천원)", color_continuous_scale="Oranges")
        fig3.update_traces(texttemplate='%{text:,.0f}천원', textposition='outside')
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        st.subheader("💳 채무 보유액 Top 10")
        debt_df = df_records[df_records['재산 구분'].str.contains('채무', na=False)].groupby('성명')['현재가액(천원)'].sum().reset_index()
        debt_df = debt_df.sort_values('현재가액(천원)', ascending=False).head(10)
        fig4 = px.bar(debt_df, x="성명", y="현재가액(천원)",
                      text="현재가액(천원)", color="현재가액(천원)", color_continuous_scale="Reds")
        fig4.update_traces(texttemplate='%{text:,.0f}천원', textposition='outside')
        st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")

    st.subheader("🏢 전체 재산 구분별 분포")
    dist = df_records.groupby("재산 구분")['현재가액(천원)'].sum().reset_index()
    dist = dist[dist['현재가액(천원)'] > 0]

    fig5 = px.pie(dist, values='현재가액(천원)', names='재산 구분', hole=0.4)
    fig5.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig5, use_container_width=True)

elif menu == "💼 주식 포트폴리오":
    st.title("💼 국회의원 주식 포트폴리오 분석")

    # Extract stocks
    stock_df = df_records[df_records['재산 구분'] == '증권'].copy()

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
                '가액(천원)': row['현재가액(천원)'],
                '의원': row['성명']
            })

    if all_stocks:
        stock_counter = Counter([s['회사명'] for s in all_stocks])

        # Top 20 stocks
        stock_results = []
        for company, count in stock_counter.most_common(20):
            holders = set(s['의원'] for s in all_stocks if s['회사명'] == company)
            total_value = sum(s['가액(천원)'] for s in all_stocks if s['회사명'] == company)
            stock_results.append({
                '회사명': company,
                '보유건수': count,
                '보유인원': len(holders),
                '총가액(천원)': total_value
            })

        stock_df_display = pd.DataFrame(stock_results)

        st.subheader("📈 인기 주식 TOP 20")

        col1, col2 = st.columns(2)

        with col1:
            fig1 = px.bar(stock_df_display.head(15), x='회사명', y='보유인원',
                         text='보유인원', color='보유인원', color_continuous_scale='Blues',
                         title='보유 인원 기준')
            fig1.update_traces(textposition='outside')
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            fig2 = px.bar(stock_df_display.head(15), x='회사명', y='총가액(천원)',
                         text='총가액(천원)', color='총가액(천원)', color_continuous_scale='Greens',
                         title='총 가액 기준')
            fig2.update_traces(texttemplate='%{text:,.0f}천원', textposition='outside')
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")
        st.subheader("📊 상세 데이터")
        stock_df_display['총가액(원)'] = stock_df_display['총가액(천원)'].apply(lambda x: format_korean_currency(x))
        st.dataframe(
            stock_df_display[['회사명', '보유건수', '보유인원', '총가액(원)']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("주식 데이터가 없습니다.")

elif menu == "🚗 자동차 분석":
    st.title("🚗 국회의원 자동차 보유 분석")
    st.subheader("차량 3대 이상 보유 현황")

    car_df = df_records[df_records['재산의 종류'] == '자동차'].copy()
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
    car_count_df = car_count_df[car_count_df['총대수'] >= 3].sort_values('총대수', ascending=False)

    if not car_count_df.empty:
        col1, col2 = st.columns([2, 1])

        with col1:
            fig = px.bar(car_count_df.head(15), x='성명', y='총대수',
                       text='총대수', color='총가액(천원)', color_continuous_scale='Greens',
                       title=f'차량 다수 보유자 TOP 15')
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.metric("3대 이상 보유자", f"{len(car_count_df)}명")
            st.metric("최다 보유", f"{int(car_count_df['총대수'].max())}대")
            st.metric("평균 보유", f"{car_count_df['총대수'].mean():.1f}대")

        st.markdown("---")
        car_count_df['총가액(원)'] = car_count_df['총가액(천원)'].apply(lambda x: format_korean_currency(x))
        st.dataframe(
            car_count_df[['성명', '총대수', '총가액(원)']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("차량 3대 이상 보유자가 없습니다.")

elif menu == "🏠 부동산 분석":
    st.title("🏠 국회의원 부동산 보유 분석")

    tab1, tab2 = st.tabs(["🏢 수도권 아파트", "🏞️ 토지 보유"])

    with tab1:
        st.subheader("수도권 아파트 보유 현황 (본인+배우자)")

        apt_df = df_records[(df_records['재산의 종류'] == '아파트') &
                           (df_records['본인과의 관계'].isin(['본인', '배우자']))].copy()
        capital_keywords = ['서울', '경기', '인천']
        apt_df['is_capital'] = apt_df['소재지 면적 등 권리의 명세'].apply(
            lambda x: any(kw in str(x) for kw in capital_keywords) if pd.notna(x) else False
        )

        capital_apts = apt_df[apt_df['is_capital']].groupby('성명').agg({
            '현재가액(천원)': ['count', 'sum']
        }).reset_index()
        capital_apts.columns = ['성명', '아파트수', '총가액(천원)']
        capital_apts = capital_apts.sort_values('아파트수', ascending=False)

        if not capital_apts.empty:
            col1, col2 = st.columns([2, 1])

            with col1:
                fig = px.bar(capital_apts.head(15), x='성명', y='아파트수',
                           text='아파트수', color='총가액(천원)', color_continuous_scale='Blues',
                           title='수도권 아파트 보유 TOP 15')
                fig.update_traces(textposition='outside')
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.metric("총 보유자", f"{len(capital_apts)}명")
                st.metric("총 아파트", f"{int(capital_apts['아파트수'].sum())}채")
                st.metric("총 가액", format_korean_currency(capital_apts['총가액(천원)'].sum()))

            st.markdown("---")
            capital_apts['총가액(원)'] = capital_apts['총가액(천원)'].apply(lambda x: format_korean_currency(x))
            st.dataframe(
                capital_apts[['성명', '아파트수', '총가액(원)']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("수도권 아파트 데이터가 없습니다.")

    with tab2:
        st.subheader("토지 보유 현황")

        land_df = df_records[df_records['재산 구분'] == '토지'].groupby('성명').agg({
            '현재가액(천원)': ['count', 'sum']
        }).reset_index()
        land_df.columns = ['성명', '필지수', '총가액(천원)']
        land_df = land_df.sort_values('총가액(천원)', ascending=False)

        col1, col2 = st.columns([2, 1])

        with col1:
            fig = px.bar(land_df.head(15), x='성명', y='총가액(천원)',
                       text='총가액(천원)', color='필지수', color_continuous_scale='Greens',
                       title='토지 보유액 TOP 15')
            fig.update_traces(texttemplate='%{text:,.0f}천원', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.metric("총 보유자", f"{len(land_df)}명")
            st.metric("총 필지", f"{int(land_df['필지수'].sum())}필지")
            st.metric("총 가액", format_korean_currency(land_df['총가액(천원)'].sum()))

        st.markdown("---")
        land_df['총가액(원)'] = land_df['총가액(천원)'].apply(lambda x: format_korean_currency(x))
        st.dataframe(
            land_df[['성명', '필지수', '총가액(원)']],
            use_container_width=True,
            hide_index=True
        )

elif menu == "👫 배우자 재산 비교":
    st.title("👫 본인 vs 배우자 재산 비교")

    person_assets = df_records[df_records['본인과의 관계'] == '본인'].groupby('성명')['현재가액(천원)'].sum().reset_index()
    person_assets.columns = ['성명', '본인재산(천원)']

    spouse_assets = df_records[df_records['본인과의 관계'] == '배우자'].groupby('성명')['현재가액(천원)'].sum().reset_index()
    spouse_assets.columns = ['성명', '배우자재산(천원)']

    comparison = person_assets.merge(spouse_assets, on='성명', how='outer').fillna(0)
    comparison['총재산(천원)'] = comparison['본인재산(천원)'] + comparison['배우자재산(천원)']
    comparison['배우자비율(%)'] = (comparison['배우자재산(천원)'] / comparison['총재산(천원)'] * 100).round(1)

    spouse_rich = comparison[comparison['배우자재산(천원)'] > comparison['본인재산(천원)']].sort_values('배우자비율(%)', ascending=False)

    st.subheader(f"배우자 재산이 더 많은 경우 ({len(spouse_rich)}명)")

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = px.bar(spouse_rich.head(15), x='성명', y='배우자비율(%)',
                   text='배우자비율(%)', color='배우자재산(천원)', color_continuous_scale='Purples',
                   title='배우자 재산 비율 TOP 15')
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.metric("평균 배우자 비율", f"{spouse_rich['배우자비율(%)'].mean():.1f}%")
        st.metric("최고 배우자 비율", f"{spouse_rich['배우자비율(%)'].max():.1f}%")
        st.metric("총 배우자 재산", format_korean_currency(spouse_rich['배우자재산(천원)'].sum()))

    st.markdown("---")
    st.subheader("상세 데이터")
    spouse_rich['본인재산(원)'] = spouse_rich['본인재산(천원)'].apply(lambda x: format_korean_currency(x))
    spouse_rich['배우자재산(원)'] = spouse_rich['배우자재산(천원)'].apply(lambda x: format_korean_currency(x))
    spouse_rich['총재산(원)'] = spouse_rich['총재산(천원)'].apply(lambda x: format_korean_currency(x))

    st.dataframe(
        spouse_rich[['성명', '본인재산(원)', '배우자재산(원)', '총재산(원)', '배우자비율(%)']],
        use_container_width=True,
        hide_index=True
    )

elif menu == "🌍 해외 자산":
    st.title("🌍 국회의원 해외 자산 보유 현황")

    # 해외 자산 정확한 패턴 매칭
    foreign_patterns = [
        r'(미국|캐나다|호주|영국|프랑스|독일|일본|중국|싱가포르|홍콩)\s+([\w]+(?:주|도|성|현|시))',
        r'\(미국\)|\(캐나다\)|\(호주\)|\(영국\)|\(일본\)|\(중국\)',
        r'[A-Z][a-z]+\s+of\s+[A-Z]',
    ]

    foreign_assets = []
    for idx, row in df_records.iterrows():
        if row['현재가액(천원)'] <= 0:
            continue

        location = str(row['소재지 면적 등 권리의 명세'])

        # 은행명 오검출 제외
        if '은행' in location and not any(re.search(pattern, location) for pattern in foreign_patterns):
            continue

        # 패턴 매칭
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
                foreign_by_person[name] = {'건수': 0, '총가액(천원)': 0, '자산목록': []}
            foreign_by_person[name]['건수'] += 1
            foreign_by_person[name]['총가액(천원)'] += asset['가액(천원)']
            foreign_by_person[name]['자산목록'].append(f"{asset['재산종류']} ({asset['위치'][:30]}...)")

        sorted_foreign = sorted(foreign_by_person.items(), key=lambda x: x[1]['총가액(천원)'], reverse=True)

        foreign_results = []
        for name, data in sorted_foreign:
            foreign_results.append({
                '성명': name,
                '건수': data['건수'],
                '총가액(천원)': data['총가액(천원)'],
                '자산': ', '.join(data['자산목록'][:3])
            })

        foreign_df = pd.DataFrame(foreign_results)

        col1, col2 = st.columns([2, 1])

        with col1:
            fig = px.bar(foreign_df.head(15), x='성명', y='총가액(천원)',
                       text='총가액(천원)', color='건수', color_continuous_scale='Oranges',
                       title=f'해외 자산 보유 TOP 15')
            fig.update_traces(texttemplate='%{text:,.0f}천원', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.metric("해외 자산 보유자", f"{len(foreign_df)}명")
            st.metric("총 해외 자산", f"{foreign_df['건수'].sum()}건")
            st.metric("총 가액", format_korean_currency(foreign_df['총가액(천원)'].sum()))

        st.markdown("---")
        st.subheader("상세 데이터")
        foreign_df['총가액(원)'] = foreign_df['총가액(천원)'].apply(lambda x: format_korean_currency(x))
        st.dataframe(
            foreign_df[['성명', '건수', '총가액(원)', '자산']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("해외 자산 데이터가 없습니다.")

elif menu == "국회의원별 상세 조회":
    st.title("👤 국회의원별 상세 조회")

    members = sorted(df_totals['성명'].dropna().unique())
    selected_member = st.sidebar.selectbox("의원을 선택하세요", members)

    st.markdown("---")

    mem_total = df_totals[df_totals['성명'] == selected_member].iloc[0]
    mem_records = df_records[df_records['성명'] == selected_member]

    # Summary Metrics
    c1, c2, c3 = st.columns(3)

    val_current = mem_total['현재가액(천원)']
    val_net = mem_total['순증감액(천원)']

    c1.metric("🔹 총 현재가액", format_currency(val_current), delta=format_korean_currency(val_current), delta_color="off")
    c2.metric("🔹 총 순증감액", format_currency(val_net), delta=format_korean_currency(val_net), delta_color="off")
    c3.metric("🔹 직위", mem_total['직위'])

    st.markdown("---")

    st.subheader(f"📊 {selected_member} 의원 재산 분석")
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        type_sum = mem_records.groupby("재산 구분")['현재가액(천원)'].sum().reset_index()
        type_sum = type_sum[type_sum['현재가액(천원)'] > 0]
        if not type_sum.empty:
            fig_type = px.pie(type_sum, values='현재가액(천원)', names='재산 구분', title="재산 구분별 비율", hole=0.3)
            st.plotly_chart(fig_type, use_container_width=True)
        else:
            st.info("시각화할 재산(가액 > 0)이 없습니다.")

    with col_chart2:
        rel_sum = mem_records.groupby("본인과의 관계")['현재가액(천원)'].sum().reset_index()
        rel_sum = rel_sum[rel_sum['현재가액(천원)'] > 0]
        if not rel_sum.empty:
            fig_rel = px.pie(rel_sum, values='현재가액(천원)', names='본인과의 관계', title="소유자별 비율", hole=0.3)
            st.plotly_chart(fig_rel, use_container_width=True)
        else:
            st.info("시각화할 재산(가액 > 0)이 없습니다.")

    st.markdown("---")
    st.subheader("📋 상세 재산 내역 (단위: 천원)")

    # Display table beautifully
    st.dataframe(
        mem_records[["본인과의 관계", "재산 구분", "재산의 종류", "소재지 면적 등 권리의 명세",
                     "종전가액(천원)", "증가액(천원)", "감소액(천원)", "현재가액(천원)", "변동사유"]],
        use_container_width=True,
        hide_index=True
    )
