import os, requests, pandas as pd

from datetime import datetime, timedelta

import time



# 💡 1. 본인의 네이버 API 키를 입력하세요 (따옴표 사이에 넣기)

CLIENT_ID = "JKZCSpCJtgKVj7pO4Uj7"

CLIENT_SECRET = "UANQpOV5hX"



# 💡 2. 파일이 자동으로 저장될 폴더 경로입니다.

TARGET_FOLDER = "C:/뉴스스크랩"



def get_naver_news_bulk(keyword):
    
    url = "https://openapi.naver.com/v1/search/news.json"
    
    headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET}
    
    all_items = []
    

    
    # 100개씩 총 10번 연속 호출하여 최대 1000개의 최신 뉴스를 긁어옵니다.
    
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
            
            print(f"오류 발생(코드 {res.status_code}), 수집을 중단하고 다음 단계로 진행합니다.")
            
            break
        
    return all_items



def save_to_excel():
    
    keyword = "디스플레이"
    
    print("네이버에서 최신 뉴스 데이터를 연속 수집 중입니다...")
    
    items = get_naver_news_bulk(keyword)
    
    print(f"총 {len(items)}개의 뉴스를 검색했습니다. 조건별 필터링을 시작합니다.")
    

    
    news_list = []
    
    now = datetime.now()
    

    
    # [시간 조건 설정] 이번 주 일요일 00:00:00 ~ 이번 주 목요일 18:00:00
    
    if now.weekday() == 6:
        
        sunday_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
    else:
        
        sunday_start = (now - timedelta(days=now.weekday() + 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
    thursday_end = now.replace(hour=18, minute=0, second=0, microsecond=0)
    

    
    print(f"수집 대상 기간: {sunday_start.strftime('%Y-%m-%d %H:%M:%S')} ~ {thursday_end.strftime('%Y-%m-%d %H:%M:%S')}")
    


    for item in items:
        
        title = item['title'].replace("<b>", "").replace("</b>", "").replace("&quot;", '"')
        
        desc = item['description'].replace("<b>", "").replace("</b>", "").replace("&quot;", '"')
        

        
        pub_date_str = item['pubDate']
        
        pub_date = datetime.strptime(pub_date_str[:-6], "%a, %d %b %Y %H:%M:%S")
        

        
        if keyword in title or keyword in desc:
            
            if sunday_start <= pub_date <= thursday_end:
                
                news_list.append({
                    
                    "뉴스 발행시간": pub_date.strftime("%Y-%m-%d %H:%M:%S"),
                    
                    "뉴스 제목": title,
                    
                    "URL": item['originallink'] if item['originallink'] else item['link'],
                    
                    "스크랩 수행시간": now.strftime("%Y-%m-%d %H:%M:%S")
                    
                })
                

            
    if not news_list:
        
        print("지정한 기간 동안 조건에 맞는 뉴스가 없습니다.")
        
        return
    

        
    df = pd.DataFrame(news_list)
    
    df = df.drop_duplicates(subset=['URL'], keep='first')
    

    
    # 요청하신 순서대로 열 배치 고정
    
    df = df[["뉴스 발행시간", "뉴스 제목", "URL", "스크랩 수행시간"]]
    

        
    if not os.path.exists(TARGET_FOLDER):
        
        os.makedirs(TARGET_FOLDER)
        

        
    file_name = f"디스플레이_뉴스_{now.strftime('%Y-%m-%d')}.xlsx"
    
    full_path = os.path.join(TARGET_FOLDER, file_name)
    
    df.to_excel(full_path, index=False)
    
    print(f"✨ 성공! 총 {len(df)}건의 뉴스가 지정된 열 순서로 저장되었습니다: {full_path}")
    
save_to_excel()
