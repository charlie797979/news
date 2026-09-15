from datetime import datetime
import streamlit as st

st.set_page_config(
    page_title="일일 업무보고서 생성기", page_icon="📝", layout="centered"
)

st.title("📝 일일 업무보고서 생성기")

# 1. 오늘 날짜 자동 불러오기
today = datetime.now()
selected_date = st.date_input("보고 날짜 선택", today)

# 날짜 포맷팅 (YYYY년 MM월 DD일)
date_str = selected_date.strftime("%Y년 %m월 %d일")

# 2. 업무 내용 입력
work_detail = st.text_area(
    "업무 내용 작성", value="'업무 대기'", height=100
)

# 3. 업무보고서 템플릿 분리 (제목 / 본문)
title_text = f"{date_str} 업무보고입니다."

body_text = f"""안녕하십니까? 주식회사 셀바이오휴먼텍 재택근로자 한철희입니다.
{date_str} 업무보고드립니다.

{work_detail}

이상으로 업무보고를 마치도록 하겠습니다.
감사합니다."""

st.divider()

# 4. 결과 출력 및 분리된 복사 기능
st.subheader("📋 완성된 업무보고서")
st.caption("💡 각 박스 우측 상단의 **복사 아이콘(📋)**을 누르면 해당 내용만 클립보드에 복사됩니다.")

# 제목 박스
st.markdown("**1. 보고서 제목**")
st.code(title_text, language=None)

# 본문 박스
st.markdown("**2. 보고서 본문**")
st.code(body_text, language=None)
