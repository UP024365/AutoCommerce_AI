import requests
import yaml
import os

def load_keys():
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def fetch_real_naver_products(keyword, display_count=10):
    keys = load_keys()
    client_id = keys['naver_client_id']
    client_secret = keys['naver_client_secret']
    
    # 네이버 쇼핑 검색 API 엔드포인트
    url = f"https://openapi.naver.com/v1/search/shop.json?query={keyword}&display={display_count}"
    
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        items = response.json().get('items', [])
        products = []
        for item in items:
            # 우리 시스템 규격에 맞게 데이터 가공
            products.append({
                "상태": "수집완료",
                "원본상품명": item['title'].replace('<b>', '').replace('</b>', ''), # HTML 태그 제거
                "AI최적화명": "",
                "원가": int(item['lprice']),
                "판매가": 0, # 나중에 마진율 계산기로 설정
                "카테고리": item['category1'],
                "이미지URL": item['image'],
                "링크": item['link']
            })
        return products
    else:
        print(f"Error: {response.status_code}")
        return []