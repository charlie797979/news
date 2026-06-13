import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import io

# 💡 본인의 네이버 API 키 설정
CLIENT_ID = "JKZCSpCJtgKVj7pO4Uj7"
CLIENT_SECRET = "UANQpOV5hX"

def get_naver_news_bulk(keyword):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET}
    
    all_items = []
    for start_idx in range(1, 1000, 100):
        params = {"query": keyword, "display": 100, "start": start_idx, "sort": "date"}
        try:
            res = requests.get(url, headers=headers, params=params)
            if res.status_code == 200:
                items = res.json().get('items', [])
                if not items: 
                    break
                all_items.extend(items)
                time.sleep(0.1) 
            else:
                break
        except:
            break
    return all_items

# 🖥️ 웹 화면 레이아웃 구성
st.set_page_config(page_title="네이버 뉴스 맞춤 스크랩 시스템", page_icon="📰", layout="centered")

st.title("📰 네이버 뉴스 맞춤 스크랩 시스템")
st.write("키워드와 기간을 선택한 후 스크랩을 진행하세요. 결과는 엑셀 파일로 즉시 다운로드됩니다.")

# 1. 검색 키워드 입력
keyword = st.text_input("검색 키워드", placeholder="예: 글로벌 채용").strip()

# 날짜 자동 계산 (지난주 토요일 ~ 오늘)
now_dt = datetime.now()
current_weekday = now_dt.weekday()
if current_weekday == 6:
    days_to_last_saturday = 8
else:
    days_to_last_saturday = current_weekday + 2
last_saturday = now_dt - timedelta(days=days_to_last_saturday)

# 2. 기간 설정 입력 (달력 팝업)
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("시작 날짜", last_saturday)
with col2:
    end_date = st.date_input("종료 날짜", now_dt)

# 3. 검색 조건 선택 (라디오 버튼 - 모바일 터치 최적화 크기)
search_mode = st.radio(
    "검색 조건 선택",
    ("키워드 완벽일치 (문구가 정확히 일치하는 뉴스만)", "키워드 모두 포함 (띄어쓰기 된 단어들이 모두 포함된 뉴스)"),
    index=0
)

st.markdown("---")

# 4. 스크랩 실행 버튼 및 로직
if st.button("🚀 스크랩 시작하기", use_container_width=True):
    if not keyword:
        st.warning("⚠️ 검색어를 입력해 주세요.")
    else:
        with st.spinner("🔄 데이터를 수집 중입니다... 잠시만 기다려주세요."):
            # 날짜를 datetime 객체로 변환 및 시간 범위 최적화
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            keyword_words = keyword.split()
            items = get_naver_news_bulk(keyword)
            news_list = []
            
            for item in items:
                title = item['title'].replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&amp;", '&')
                desc = item['description'].replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&amp;", '&')
                
                link = item['link']
                press_name = "기타언론"
                
                if "naver.com" in link: press_name = "네이버뉴스"
                elif "yna.co.kr" in link: press_name = "연합뉴스"
                elif "news.kmib.co.kr" in link: press_name = "국민일보"
                elif "chosun.com" in link: press_name = "조선일보"
                elif "hani.co.kr" in link: press_name = "한겨레"
                elif "khan.co.kr" in link: press_name = "경향신문"
                elif "donga.com" in link: press_name = "동아일보"
                elif "joins.com" in link or "joongang.co.kr" in link: press_name = "중앙일보"
                elif "mk.co.kr" in link: press_name = "매일경제"
                elif "hankyung.com" in link: press_name = "한국경제"
                elif "edaily.co.kr" in link: press_name = "이데일리"
                elif "moneytoday" in link or "mt.co.kr" in link: press_name = "머니투데이"
                elif "asiatime" in link: press_name = "아시아타임즈"
                elif "fnnews.com" in link: press_name = "파이낸셜뉴스"
                else:
                    domain = link.split("//")[-1].split("/")[0]
                    press_name = domain.replace("www.", "").split(".")[0]

                pub_date_str = item['pubDate']
                pub_date = datetime.strptime(pub_date_str[:-6], "%a, %d %b %Y %H:%M:%S")
                
                is_matched = False
                if "완벽일치" in search_mode:
                    if keyword in title or keyword in desc:
                        is_matched = True
                else:
                    if all(word in title or word in desc for word in keyword_words):
                        is_matched = True

                if is_matched:
                    if start_datetime <= pub_date <= end_datetime:
                        news_list.append({
                            "뉴스 발행시간": pub_date.strftime("%Y-%m-%d %H:%M:%S"),
                            "언론사명": press_name,
                            "뉴스 제목": title,
                            "URL": item['originallink'] if item['originallink'] else item['link']
                        })
            
            if not news_list:
                st.info("ℹ️ 지정한 기간 동안 조건에 맞는 뉴스가 없습니다.")
            else:
                df = pd.DataFrame(news_list)
                df = df.drop_duplicates(subset=['URL'], keep='first')
                df = df.sort_values(by="뉴스 발행시간", ascending=True)
                df = df[["뉴스 발행시간", "언론사명", "뉴스 제목", "URL"]]
                
                # 파일을 하드디스크가 아닌 브라우저 다운로드 메모리(스트림)로 변환
                excel_data = io.BytesIO()
                with pd.ExcelWriter(excel_data, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                excel_data.seek(0)
                
                st.success(f"✨ 총 {len(df)}건의 뉴스 스크랩 완료!")
                
                # 웹 다운로드 버튼 활성화
                file_name = f"{keyword}_뉴스_{now_dt.strftime('%Y-%m-%d')}.xlsx"
                st.download_button(
                    label="📥 엑셀 파일 다운로드 받기",
                    data=excel_data,
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

# 5. 우측 하단 고정 푸터 (오류 수정 반영 완료)
st.markdown(
    """
    <style>
    .footer { position: fixed; right: 25px; bottom: 15px; font-family: Arial; font-weight: bold; font-style: italic; color: #0B192C; font-size: 14px; }
    </style>
    <div class="footer">Made by H.C.H.</div>
    """,
    unsafe_allow_html=True
)
