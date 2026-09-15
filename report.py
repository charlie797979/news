from datetime import datetime
import streamlit as st

st.set_page_config(
    page_title="일일 업무보고서 생성기", page_icon="📝", layout="centered"
)

st.title("📝 일일 업무보고서 생성기")

# 1. 오늘 날짜 자동 불러오기 (필요 시 날짜 변경 가능)
today = datetime.now()
selected_date = st.date_input("보고 날짜 선택", today)

# 날짜 포맷팅 (YYYY년 MM월 DD일)
date_str = selected_date.strftime("%Y년 %m월 %d일")

# 2. 업무 내용 입력 (기본값: '업무 대기')
work_detail = st.text_area(
    "업무 내용 작성", value="'업무 대기'", height=100
)

# 3. 업무보고서 템플릿 완성
report_text = f"""{date_str} 업무보고입니다.

안녕하십니까? 주식회사 셀바이오휴먼텍 재택근로자 한철희입니다.
{date_str} 업무보고드립니다.

{work_detail}

이상으로 업무보고를 마치도록 하겠습니다.
감사합니다."""

st.divider()

# 4. 결과 출력 및 복사 기능
st.subheader("📋 완성된 업무보고서")
st.caption(
    "💡 아래 박스 우측 상단의 **복사 아이콘(📋)**을 누르면 클립보드에 전체 내용이 복사됩니다."
)

# st.code를 활용하면 우측 상단에 원클릭 복사 버튼이 자동으로 생성됩니다.
st.code(report_text, language=None)

