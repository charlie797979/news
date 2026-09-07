import os, requests, pandas as pd
from datetime import datetime, timedelta
import time

CLIENT_ID = "JKZCSpCJtgKVj7pO4Uj7"
CLIENT_SECRET = "UANQpOV5hX"
TARGET_FOLDER = "C:/뉴스스크랩"

def get_naver_news_bulk(keyword):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET}
    all_items = []
    
    for start_idx in range(1, 1000, 100):
        params = {"query": keyword, "display": 100, "start": start_idx, "sort": "date"}
        res = requests.get(url, headers=headers, params=params)
        
        if res.status_code == 200:
            items = res.json().get('items', [])
            if not items:
                break
            all_items.extend(items)
            time.sleep(0.1)
        else:
            print(f"오류 발생(코드 {res.status_code})")
            break
            
    return all_items

def save_to_excel():
    keyword = "디스플레이"
    print("네이버 데이터 수집 중...")
    items = get_naver_news_bulk(keyword)
    print(f"API 수집 완료: 총 {len(items)}개 검색됨")
    
    if not items:
        print("❌ API 응답값에 뉴스가 전혀 없습니다.")
        return

    now = datetime.now()
    # 시작 시간: 전일 13시 00분
    start_date = (now - timedelta(days=1)).replace(hour=13, minute=0, second=0, microsecond=0)
    # 종료 시간: 현재 실행 시간
    end_date = now
    
    print(f"수집 기준 기간: {start_date.strftime('%Y-%m-%d %H:%M')} ~ {end_date.strftime('%Y-%m-%d %H:%M')}")
    
    news_list = []
    for item in items:
        title = item['title'].replace("<b>", "").replace("</b>", "").replace("&quot;", '"')
        desc = item['description'].replace("<b>", "").replace("</b>", "").replace("&quot;", '"')
        
        pub_date_str = item['pubDate']
        pub_date = datetime.strptime(pub_date_str[:-6], "%a, %d %b %Y %H:%M:%S")
        
        # 제목이나 본문에 키워드가 있고 지정한 기간 범위 내인 경우 저장
        if (keyword in title or keyword in desc) and (start_date <= pub_date <= end_date):
            news_list.append({
                "뉴스 발행시간": pub_date.strftime("%Y-%m-%d %H:%M"),
                "뉴스 제목": title,
                "URL": item['originallink'] if item['originallink'] else item['link'],
                "스크랩 수행시간": now.strftime("%Y-%m-%d %H:%M")
            })
                
    if not news_list:
        print("❌ 지정한 기간(전일 13시 ~ 현재) 내 조건에 맞는 뉴스가 없습니다.")
        return
        
    df = pd.DataFrame(news_list)
    df = df.drop_duplicates(subset=['URL'], keep='first')
    df = df[["뉴스 발행시간", "뉴스 제목", "URL", "스크랩 수행시간"]]
    
    if not os.path.exists(TARGET_FOLDER):
        os.makedirs(TARGET_FOLDER)
        
    file_name = f"디스플레이_뉴스_{now.strftime('%Y-%m-%d_%H%M')}.xlsx"
    full_path = os.path.join(TARGET_FOLDER, file_name)
    
    df.to_excel(full_path, index=False)
    print(f"✨ 성공! 총 {len(df)}건의 뉴스가 저장되었습니다: {full_path}")

save_to_excel()

