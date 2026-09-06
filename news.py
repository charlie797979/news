import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import io
from bs4 import BeautifulSoup
from google import genai

# 💡 Streamlit Secrets에서 API 키 불러오기
try:
    CLIENT_ID = st.secrets["CLIENT_ID"]
    CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("⚠️ Secrets 설정이 올바르지 않습니다. Streamlit Cloud settings의 Secrets에 키 정보를 입력해 주세요.")
    st.stop()

# Gemini 클라이언트 초기화
client = genai.Client(api_key=GEMINI_API_KEY)

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

# 1. URL에서 기사 본문 텍스트 추출 (네이버 뉴스 본문 구조 보완)
def fetch_article_text(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 네이버 뉴스 특화 본문 추출
            article = soup.select_one('#newsct_article') or soup.select_one('#articleBodyContents')
            if article:
                for target in article(["script", "style", "span", "a"]):
                    target.decompose()
                return article.get_text(separator=' ', strip=True)[:2500]
            
            # 일반 언론사 사이트 추출
            for script in soup(["script", "style", "header", "footer", "nav", "iframe"]):
                script.decompose()
            return soup.get_text(separator=' ', strip=True)[:2500]
    except Exception:
        pass
    return ""

# 2. Gemini API 두 문장 요약
def summarize_with_gemini(title, text, fallback_desc):
    content_to_summarize = text if len(text) > 150 else f"제목: {title}\n요약문: {fallback_desc}"
    
    prompt = f"""
    다음 뉴스 기사 내용을 읽고 가장 중요한 핵심 내용을 정확히 한국어 **두 문장**으로 요약해 주세요.
    말줄임표(...)나 불완전한 문장을 쓰지 말고, 완성된 두 문장만 깔끔하게 출력하세요.

    [기사 내용]
    {content_to_summarize}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text.strip()
    except Exception:
        return fallback_desc

# 🖥️ 웹 화면 레이아웃
st.set_page_config(page_title="네이버 뉴스 맞춤 스크랩 시스템", page_icon="📰", layout="centered")

st.title("📰 네이버 뉴스 맞춤 스크랩 시스템")
st.write("키워드와 기간을 선택한 후 스크랩을 진행하세요. 결과는 엑셀 파일로 즉시 다운로드됩니다.")

# 1. 검색 키워드 입력
keyword = st.text_input("검색 키워드", value="셀바이오휴먼텍", placeholder="예: 셀바이오휴먼텍").strip()

# 날짜/시간 자동 계산 (전일 13:00 ~ 현재)
now_dt = datetime.now()
yesterday_13pm = (now_dt - timedelta(days=1)).replace(hour=13, minute=0, second=0, microsecond=0)

# 2. 기간 및 시간 설정
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("시작 날짜", yesterday_13pm.date())
    start_time = st.time_input("시작 시간", yesterday_13pm.time())
with col2:
    end_date = st.date_input("종료 날짜", now_dt.date())
    end_time = st.time_input("종료 시간", now_dt.time())

# 3. 검색 조건
search_mode = st.radio(
    "검색 조건 선택",
    ("키워드 완벽일치 (문구가 정확히 일치하는 뉴스만)", "키워드 모두 포함 (띄어쓰기 된 단어들이 모두 포함된 뉴스)"),
    index=0
)

st.markdown("---")

# 4. 스크랩 시작
if st.button("🚀 스크랩 시작하기", use_container_width=True):
    if not keyword:
        st.warning("⚠️ 검색어를 입력해 주세요.")
    else:
        with st.spinner("🔄 뉴스를 수집하는 중입니다..."):
            start_datetime = datetime.combine(start_date, start_time)
            end_datetime = datetime.combine(end_date, end_time)
            
            keyword_words = keyword.split()
            items = get_naver_news_bulk(keyword)
            news_list = []
            
            matched_items = []
            for item in items:
                title = item['title'].replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&amp;", '&')
                desc = item['description'].replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&amp;", '&')
                
                pub_date_str = item['pubDate']
                pub_date = datetime.strptime(pub_date_str[:-6], "%a, %d %b %Y %H:%M:%S")
                
                is_matched = False
                if "완벽일치" in search_mode:
                    if keyword in title or keyword in desc:
                        is_matched = True
                else:
                    if all(word in title or word in desc for word in keyword_words):
                        is_matched = True

                if is_matched and start_datetime <= pub_date <= end_datetime:
                    matched_items.append((item, title, desc, pub_date))

            if not matched_items:
                st.info("ℹ️ 지정한 기간 동안 조건에 맞는 뉴스가 없습니다.")
            else:
                progress_bar = st.progress(0)
                total_count = len(matched_items)

                for idx, (item, title, desc, pub_date) in enumerate(matched_items):
                    link = item['link']
                    # 네이버 뉴스 링크를 우선 사용하여 본문 추출 성공률 극대화
                    target_url = link if "naver.com" in link else (item['originallink'] if item['originallink'] else link)
                    
                    # 언론사명 판별
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

                    # 본문 수집 및 Gemini 요약
                    article_text = fetch_article_text(target_url)
                    summary_text = summarize_with_gemini(title, article_text, desc)
                    
                    news_list.append({
                        "뉴스 발행시간": pub_date.strftime("%Y-%m-%d %H:%M:%S"),
                        "언론사명": press_name,
                        "뉴스 제목": title,
                        "URL": item['originallink'] if item['originallink'] else link,
                        "뉴스 두 문장 요약": summary_text
                    })
                    
                    progress_bar.progress((idx + 1) / total_count)

                df = pd.DataFrame(news_list)
                df = df.drop_duplicates(subset=['URL'], keep='first')
                df = df.sort_values(by="뉴스 발행시간", ascending=True)
                df = df[["뉴스 발행시간", "언론사명", "뉴스 제목", "URL", "뉴스 두 문장 요약"]]
                
                excel_data = io.BytesIO()
                with pd.ExcelWriter(excel_data, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                excel_data.seek(0)
                
                st.success(f"✨ 총 {len(df)}건의 뉴스 스크랩 및 AI 요약 완료!")
                
                file_name = f"{keyword}_뉴스_{now_dt.strftime('%Y-%m-%d_%H%M')}.xlsx"
                st.download_button(
                    label="📥 엑셀 파일 다운로드 받기",
                    data=excel_data,
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

# 📄 푸터
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
