import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import io

# 💡 Streamlit Secrets에서 API 키 불러오기
try:
    CLIENT_ID = st.secrets["CLIENT_ID"]
    CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("⚠️ Secrets 설정이 올바르지 않습니다. Streamlit Cloud settings의 Secrets에 키 정보를 입력해 주세요.")
    st.stop()

# 네이버 뉴스 API 호출
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
            else:
                break
        except Exception:
            break
    return all_items

# Gemini REST API 호출 (v1 정식 버전 엔드포인트 적용)
def refine_summary_with_gemini(title, desc):
    # Google AI Studio 표준 REST Endpoint (v1)
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    
    prompt = f"""
    다음은 뉴스 기사의 제목과 요약문입니다. 
    내용이 중간에 잘렸거나 어색하다면 문맥을 자연스럽게 보완하여 **정확히 완결된 두 문장**으로 다시 작성해 주세요.
    말줄임표(...)나 불완전한 문장을 사용하지 마시고, 완성된 두 문장만 깔끔하게 출력해 주세요.

    [기사 제목]
    {title}

    [기사 요약]
    {desc}
    """
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        if res.status_code == 200:
            result = res.json()
            text = result['candidates'][0]['content']['parts'][0]['text'].strip()
            if text:
                return text, None
        else:
            return desc, f"API 에러코드: {res.status_code} ({res.text})"
    except Exception as e:
        return desc, f"요약 에러: {str(e)}"
    return desc, "응답 없음"

# 🖥️ 웹 화면 레이아웃
st.set_page_config(page_title="네이버 뉴스 맞춤 스크랩 시스템", page_icon="📰", layout="centered")

st.title("📰 네이버 뉴스 맞춤 스크랩 시스템")
st.write("키워드와 기간을 선택한 후 스크랩을 진행하세요. 결과는 엑셀 파일로 즉시 다운로드됩니다.")

# 1. 검색 키워드 입력
keyword = st.text_input("검색 키워드", value="셀바이오휴먼텍", placeholder="예: 셀바이오휴먼텍").strip()

# 🕒 한국 표준시(KST, UTC+9) 기준 현재 시간 적용
KST = timezone(timedelta(hours=9))
now_dt = datetime.now(KST)

# 전일 13:00 ~ 현재 시간 자동 설정
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
        with st.spinner("🔄 뉴스를 수집하고 AI 요약을 생성 중입니다..."):
            start_datetime = datetime.combine(start_date, start_time).replace(tzinfo=KST)
            end_datetime = datetime.combine(end_date, end_time).replace(tzinfo=KST)
            
            keyword_words = keyword.split()
            items = get_naver_news_bulk(keyword)
            
            matched_items = []
            for item in items:
                title = item['title'].replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&amp;", '&')
                desc = item['description'].replace("<b>", "").replace("</b>", "").replace("&quot;", '"').replace("&amp;", '&')
                
                pub_date_str = item['pubDate']
                pub_date_naive = datetime.strptime(pub_date_str[:-6], "%a, %d %b %Y %H:%M:%S")
                pub_date = pub_date_naive.replace(tzinfo=timezone.utc).astimezone(KST)
                
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
                news_list = []
                error_logs = []
                
                for item, title, desc, pub_date in matched_items:
                    link = item['link']
                    target_url = item['originallink'] if item['originallink'] else link
                    
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

                    summary_text, err = refine_summary_with_gemini(title, desc)
                    if err:
                        error_logs.append(err)
                    
                    news_list.append({
                        "뉴스 발행시간": pub_date.strftime("%Y-%m-%d %H:%M:%S"),
                        "언론사명": press_name,
                        "뉴스 제목": title,
                        "URL": target_url,
                        "뉴스 두 문장 요약": summary_text
                    })

                if error_logs:
                    st.error(f"⚠️ Gemini API 호출 중 문제가 발생했습니다: {error_logs[0]}")

                df = pd.DataFrame(news_list)
                df = df.drop_duplicates(subset=['URL'], keep='first')
                df = df.sort_values(by="뉴스 발행시간", ascending=True)
                df = df[["뉴스 발행시간", "언론사명", "뉴스 제목", "URL", "뉴스 두 문장 요약"]]
                
                excel_data = io.BytesIO()
                with pd.ExcelWriter(excel_data, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                excel_data.seek(0)
                
                st.success(f"✨ 총 {len(df)}건 스크랩 처리 완료!")
                
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
