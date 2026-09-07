import os, requests, pandas as pd
from datetime import datetime
import time, io
import streamlit as st
from bs4 import BeautifulSoup
from google import genai

# 💡 1. Gemini API 키 및 최신 Client 설정
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

def get_gemini_client():
    if GEMINI_API_KEY:
        try:
            return genai.Client(api_key=GEMINI_API_KEY)
        except Exception:
            return None
    return None

# URL 본문 크롤링 및 Gemini 2문장 요약 함수
def summarize_from_url(url, client):
    content = ""
    title = "제목 추출 실패"
    
    # 1. 크롤링 (User-Agent 헤더 강화)
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 제목 추출
            if soup.title and soup.title.get_text().strip():
                title = soup.title.get_text().strip()
            elif soup.find('h1'):
                title = soup.find('h1').get_text().strip()

            # 본문 추출 (p 태그 및 article 영역 대응)
            article_body = soup.find('article') or soup.find('div', class_=lambda x: x and 'article' in x.lower())
            if article_body:
                paragraphs = article_body.find_all('p')
            else:
                paragraphs = soup.find_all('p')
                
            content = " ".join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 20])
    except Exception as e:
        return title, f"페이지 수집 실패({type(e).__name__})"

    if not content or len(content) < 40:
        return title, "본문 수집 불가 (보안/접근 제한 사이트)"

    if not client:
        return title, "실패: GEMINI_API_KEY 미설정 또는 Client 생성 실패"

    # 2. 최신 SDK Gemini API 호출
    prompt = f"다음 뉴스 내용의 핵심만 정확히 2문장으로 간결하게 요약해 주세요:\n\n{content[:3000]}"
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        time.sleep(0.3)
        return title, response.text.strip()
    except Exception as e:
        # 2.5-flash 지원 전이거나 실패 시 1.5-flash 재시도
        try:
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt,
            )
            time.sleep(0.3)
            return title, response.text.strip()
        except Exception as inner_e:
            return title, f"요약 실패({type(inner_e).__name__})"

# 🖥️ 웹 화면 레이아웃
st.set_page_config(page_title="URL 뉴스 AI 2문장 요약기", page_icon="🔗", layout="centered")

st.title("🔗 URL 전용 뉴스 2문장 요약기")
st.write("요약하고 싶은 뉴스 URL 링크를 아래 상자에 붙여넣어 주세요.")

urls_input = st.text_area(
    "뉴스 URL 목록 (한 줄에 하나씩 입력)",
    placeholder="https://news.naver.com/...\nhttps://v.daum.net/...\nhttps://www.chosun.com/...",
    height=200
)

st.markdown("---")

if st.button("🚀 URL 요약 및 엑셀 생성", use_container_width=True):
    url_list = [u.strip() for u in urls_input.split('\n') if u.strip()]
    
    if not url_list:
        st.warning("⚠️ 요약할 URL을 하나 이상 입력해 주세요.")
    else:
        client = get_gemini_client()
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, url in enumerate(url_list):
            status_text.text(f"⏳ ({idx+1}/{len(url_list)}) 분석 중: {url}")
            
            title, summary = summarize_from_url(url, client)
            
            try:
                domain = url.split("//")[-1].split("/")[0].replace("www.", "")
            except Exception:
                domain = "기타"

            results.append({
                "수집일시": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "도메인/출처": domain,
                "뉴스 제목": title,
                "URL": url,
                "Gemini 2문장 요약": summary
            })
            
            progress_bar.progress((idx + 1) / len(url_list))
        
        status_text.success("✅ 모든 작업 완료!")
        
        df = pd.DataFrame(results)
        excel_data = io.BytesIO()
        with pd.ExcelWriter(excel_data, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        excel_data.seek(0)
        
        st.dataframe(df[["뉴스 제목", "Gemini 2문장 요약", "URL"]], use_container_width=True)
        
        file_name = f"뉴스_URL_요약_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        st.download_button(
            label="📥 요약 결과 엑셀 다운로드",
            data=excel_data,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

# 📄 하단 푸터
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
