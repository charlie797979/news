import os, requests, pandas as pd
from datetime import datetime, timedelta, time as dttime
import time, io
import streamlit as st
from bs4 import BeautifulSoup
import google.generativeai as genai

# 💡 1. 네이버 API 키 설정
CLIENT_ID = "JKZCSpCJtgKVj7pO4Uj7"
CLIENT_SECRET = "UANQpOV5hX"

# 💡 2. Gemini API 키 불러오기
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

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
        except Exception:
            break
    return all_items

# 뉴스 URL 본문 크롤링 및 Gemini 2문장 요약 함수
def summarize_news(url, description):
    content = ""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=3)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            paragraphs = soup.find_all('p')
            content = " ".join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 30])
    except Exception:
        pass
    
    # 크롤링 실패 시 기본 description 사용
    if not content or len(content) < 50:
        content = description

    prompt = f"다음 뉴스 내용을 정확히 두 문장으로 핵심만 간결하게 요약해 주세요:\n\n{content}"
    
    if not GEMINI_API_KEY:
        return f"[기본요약] {description}"

    # 모델 생성 방식 보완
    try:
        # SDK 엔드포인트 수정을 위한 GenerativeModel 직접 선언
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        time.sleep(0.4)
        return response.text.strip()
    except Exception as e:
        # NotFound 등 API 오류 시 무조건 실패 처리하는 대신 기본 description 반환
        return f"[요약 대체] {description}"

# 🖥️ 웹 화면 레이아웃 구성
st.set_page_config(page_title="네이버 뉴스 맞춤 스크랩 시스템", page_icon="📰", layout="centered")

st.title("📰 네이버 뉴스 맞춤 스크랩 시스템")
st.write("키워드와 기간을 선택한 후 스크랩을 진행하세요. Gemini가 뉴스를 2문장으로 요약해 줍니다.")

# 1. 검색 키워드 입력
keyword = st.text_input("검색 키워드", placeholder="예: 글로벌 채용").strip()

# 한국 시간(KST = UTC + 9시간) 기준 시각 보정
now_dt = datetime.utcnow() + timedelta(hours=9)
yesterday_dt = now_dt - timedelta(days=1)

default_start_time = dttime(13, 0)
default_end_time = now_dt.time()

# 2. 기간 및 시간 설정 입력
col1, col2, col3, col4 = st.columns([2, 1.5, 2, 1.5])

with col1:
    start_date = st.date_input("시작 날짜", yesterday_dt)
with col2:
    start_time = st.time_input("시작 시간", default_start_time)

with col3:
    end_date = st.date_input("종료 날짜", now_dt)
with col4:
    end_time = st.time_input("종료 시간", default_end_time)

# 3. 검색 조건 선택
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
        with st.spinner("🔄 데이터를 수집하고 Gemini로 뉴스를 요약 중입니다..."):
            start_datetime = datetime.combine(start_date, start_time)
            end_datetime = datetime.combine(end_date, end_time)
            
            keyword_words = keyword.split()
            items = get_naver_news_bulk(keyword)
            news_list = []
            
            for item in items:
                title = item['title'].replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&amp;", '&')
                desc = item['description'].replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&amp;", '&')
                
                link = item['originallink'] if item['originallink'] else item['link']
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
                pub_date_utc = datetime.strptime(pub_date_str[:-6], "%a, %d %b %Y %H:%M:%S")
                pub_date = pub_date_utc + timedelta(hours=9)
                
                is_matched = False
                if "완벽일치" in search_mode:
                    if keyword in title or keyword in desc:
                        is_matched = True
                else:
                    if all(word in title or word in desc for word in keyword_words):
                        is_matched = True

                if is_matched and (start_datetime <= pub_date <= end_datetime):
                    summary = summarize_news(link, desc)
                    
                    news_list.append({
                        "뉴스 발행시간": pub_date.strftime("%Y-%m-%d %H:%M"),
                        "언론사명": press_name,
                        "뉴스 제목": title,
                        "URL": link,
                        "뉴스 요약": summary
                    })
            
            if not news_list:
                st.info(f"ℹ️ {start_datetime.strftime('%Y-%m-%d %H:%M')} ~ {end_datetime.strftime('%Y-%m-%d %H:%M')} 기간 동안 조건에 맞는 뉴스가 없습니다.")
            else:
                df = pd.DataFrame(news_list)
                df = df.drop_duplicates(subset=['URL'], keep='first')
                df = df.sort_values(by="뉴스 발행시간", ascending=True)
                df = df[["뉴스 발행시간", "언론사명", "뉴스 제목", "URL", "뉴스 요약"]]
                
                excel_data = io.BytesIO()
                with pd.ExcelWriter(excel_data, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                excel_data.seek(0)
                
                st.success(f"✨ 총 {len(df)}건의 뉴스 스크랩 완료!")
                
                file_name = f"{keyword}_뉴스_{now_dt.strftime('%Y-%m-%d_%H%M')}.xlsx"
                st.download_button(
                    label="📥 엑셀 파일 다운로드 받기",
                    data=excel_data,
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

# 📄 5. 하단 푸터
st.markdown("<br><br><br>", unsafe_allow_html=True)
st.markdown(
    """
    <div style="text-align: center; border-top: 1px solid #E0E0E0; padding-top: 20px;">
        <span style="font-family: 'Arial', sans-serif; font-size: 13px; color: #888888; letter-spacing: 1px;">
            Designed & Developed by <strong style="color: #444444; font-style: italic;">H.C.H.</strong>
        </span>
    </div>
    """,
    unsafe_allow_html=True
)
