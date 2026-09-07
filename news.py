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
            print(f"오류 발생(코드 {res.status_code}), 수집을 중단합니다.")
            break
            
    return all_items

def save_to_excel():
    keyword = "디스플레이"
    print("네이버에서 최신 뉴스 데이터를 수집 중입니다...")
    items = get_naver_news_bulk(keyword)
    print(f"총 {len(items)}개의 뉴스를 검색했습니다. 필터링을 시작합니다.")
    
    now = datetime.now()
    
    # 1. 시작 날짜: 실행 전일(어제) 13시 00분 00초
    start_date = (now - timedelta(days=1)).replace(hour=13, minute=0, second=0, microsecond=0)
    
    # 2. 종료 날짜: 현재 프로그램 실행 시간
    end_date = now
    
    # 안내 메시지에 연-월-일 시:분 형태로 출력
    print(f"수집 대상 기간: {start_date.strftime('%Y-%m-%d %H:%M')} ~ {end_date.strftime('%Y-%m-%d %H:%M')}")
    
    news_list = []
    for item in items:
        title = item['title'].replace("<b>", "").replace("</b>", "").replace("&quot;", '"')
        desc = item['description'].replace("<b>", "").replace("</b>", "").replace("&quot;", '"')
        
        pub_date_str = item['pubDate']
        pub_date = datetime.strptime(pub_date_str[:-6], "%a, %d %b %Y %H:%M:%S")
        
        if keyword in title or keyword in desc:
            if start_date <= pub_date <= end_date:
                news_list.append({
                    "뉴스 발행시간": pub_date.strftime("%Y-%m-%d %H:%M"),
                    "뉴스 제목": title,
                    "URL": item['originallink'] if item['originallink'] else item['link'],
                    "스크랩 수행시간": now.strftime("%Y-%m-%d %H:%M")
                })
                
    if not news_list:
        print("지정한 기간 동안 조건에 맞는 뉴스가 없습니다.")
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
