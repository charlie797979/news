import os, requests, pandas as pd
from datetime import datetime, timedelta
import time, io
import streamlit as st
from bs4 import BeautifulSoup
import google.generativeai as genai

# 💡 1. Gemini API 키 불러오기
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# URL 본문 크롤링 및 Gemini 2문장 요약 함수
def summarize_from_url(url):
    content = ""
    title = "제목 추출 실패"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 제목 추출 시도
            if soup.title:
                title = soup.title.get_text().strip()
            elif soup.find('h1'):
                title = soup.find('h1').get_text().strip()

            # 본문 문단 추출
            paragraphs = soup.find_all('p')
            content = " ".join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 30])
    except Exception as e:
        return title, f"페이지 수집 실패: {type(e).__name__}"

    if not content or len(content) < 50:
        return title, "본문 내용을 충분히 불러오지 못했습니다 (보안/접근 제한)"

    prompt = f"다음 뉴스/웹페이지 내용을 정확히 두 문장으로 핵심만 간결하게 요약해 주세요:\n\n{content[:3000]}"
    
    if not GEMINI_API_KEY:
        return title, "실패: GEMINI_API_KEY 미설정"

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        time.sleep(0.5) # API 호출 제한 방지
        return title, response.text.strip()
    except Exception as e:
        return title, f"요약 실패({type(e).__name__})"

# 🖥️ 웹 화면 레이아웃
st.set_page_config(page_title="URL 뉴스 AI 2문장 요약기", page_icon="🔗", layout="centered")

st.title("🔗 URL 전용 뉴스 2문장 요약기")
st.write("요약하고 싶은 뉴스 URL 링크를 아래 상자에 붙여넣어 주세요.")

# URL 입력 텍스트 에어리어
urls_input = st.text_area(
    "뉴스 URL 목록 (한 줄에 하나씩 입력)",
    placeholder="https://news.naver.com/...\nhttps://v.daum.net/...\nhttps://www.chosun.com/...",
    height=200
)

st.markdown("---")

if st.button("🚀 URL 요약 및 엑셀 생성", use_container_width=True):
    # 입력된 URL 정리 (공백 제거 및 빈 줄 제외)
    url_list = [u.strip() for u in urls_input.split('\n') if u.strip()]
    
    if not url_list:
        st.warning("⚠️ 요약할 URL을 하나 이상 입력해 주세요.")
    else:
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, url in enumerate(url_list):
            status_text.text(f"⏳ ({idx+1}/{len(url_list)}) 요약 중: {url}")
            
            title, summary = summarize_from_url(url)
            
            # 언론사/도메인 추출
            try:
                domain = url.split("//")[-1].split("/")[0].replace("www.", "")
            except:
                domain = "기타"

            results.append({
                "수집일시": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "도메인/출처": domain,
                "뉴스 제목": title,
                "URL": url,
                "Gemini 2문장 요약": summary
            })
            
            # 진행률 업데이트
            progress_bar.progress((idx + 1) / len(url_list))
        
        status_text.success("✅ 모든 URL 요약 완료!")
        
        # 데이터프레임 변환 및 엑셀 생성
        df = pd.DataFrame(results)
        excel_data = io.BytesIO()
        with pd.ExcelWriter(excel_data, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        excel_data.seek(0)
        
        # 결과 데이터 프레임 화면 표시
        st.dataframe(df[["뉴스 제목", "Gemini 2문장 요약", "URL"]], use_container_width=True)
        
        # 엑셀 다운로드 버튼
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
