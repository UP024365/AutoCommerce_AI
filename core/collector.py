import os
import time
import hmac
import hashlib
import requests
import yaml
import traceback

# [공식 예제 핵심] 시스템 타임존을 GMT로 강제 설정하여 시간 오차 방지
os.environ['TZ'] = 'GMT+0'

def load_keys():
    """config.yaml에서 API 키 로드"""
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print("❌ [Error] config.yaml 파일을 찾을 수 없습니다.")
        return {}

def generate_coupang_headers(method, path, query_str=""):
    """쿠팡 공식 예제 로직을 그대로 구현한 헤더 생성 함수"""
    keys = load_keys()
    access_key = keys.get('coupang_access_key', '').strip()
    secret_key = keys.get('coupang_secret_key', '').strip()
    
    # [공식 예제 방식] GMT 기준 타임스탬프 생성
    # 예제: datetime=time.strftime('%y%m%d')+'T'+time.strftime('%H%M%S')+'Z'
    timestamp = time.strftime('%y%m%dT%H%M%SZ', time.gmtime())
    
    # [공식 예제 방식] Message 구성 (Timestamp + Method + Path + Query)
    # 쿼리스트링에서 물음표(?)는 제외하고 파라미터만 합칩니다.
    clean_query = query_str.replace('?', '').strip()
    message = timestamp + method + path + clean_query
    
    # HMAC SHA256 서명 생성
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # 공식 예제와 동일한 Authorization 헤더 형식
    return {
        "Content-type": "application/json;charset=UTF-8",
        "Authorization": f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={timestamp}, signature={signature}"
    }

def fetch_real_naver_products(keyword, display_count=10):
    """네이버 쇼핑 검색 (기존 로직 유지)"""
    keys = load_keys()
    url = f"https://openapi.naver.com/v1/search/shop.json?query={keyword}&display={display_count}"
    headers = {
        "X-Naver-Client-Id": keys.get('naver_client_id'),
        "X-Naver-Client-Secret": keys.get('naver_client_secret')
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            items = response.json().get('items', [])
            return [{
                "상태": "수집완료",
                "원본상품명": item['title'].replace('<b>', '').replace('</b>', ''),
                "AI최적화명": "",
                "원가": int(item['lprice']),
                "판매가": 0,
                "카테고리": item['category1'],
                "이미지URL": item['image'],
                "링크": item['link']
            } for item in items]
    except Exception as e:
        print(f"🚨 네이버 수집 중 오류: {e}")
    return []

def fetch_coupang_products(max_results=10):
    """쿠팡 내 상품 수집 (공식 인증 방식 적용)"""
    print("\n" + "="*50)
    print("🚀 [LOG] 쿠팡 상품 수집 시도 중...")
    try:
        keys = load_keys()
        vendor_id = keys.get('coupang_vendor_id', '').strip()
        
        # 1. 목록 조회
        list_path = "/v2/providers/seller_api/apis/api/v1/marketplace/seller-products"
        list_query = f"vendorId={vendor_id}&maxPerPage={max_results}"
        
        headers = generate_coupang_headers("GET", list_path, list_query)
        list_url = f"https://api-gateway.coupang.com{list_path}?{list_query}"
        
        response = requests.get(list_url, headers=headers, timeout=10)
        print(f"📡 [LOG] 목록 조회 결과 코드: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ [LOG] 에러 내용: {response.text}")
            return []

        summary_data = response.json().get('data', [])
        detailed_products = []

        # 2. 상세 조회 루프
        for summary in summary_data:
            sp_id = summary.get('sellerProductId')
            detail_path = f"/v2/providers/seller_api/apis/api/v1/marketplace/seller-products/{sp_id}"
            detail_headers = generate_coupang_headers("GET", detail_path, "")
            detail_url = f"https://api-gateway.coupang.com{detail_path}"
            
            detail_res = requests.get(detail_url, headers=detail_headers, timeout=10)
            if detail_res.status_code == 200:
                res_json = detail_res.json()
                d = res_json.get('data', {})
                items = d.get('items', [])
                first_item = items[0] if items else {}
                
                images = first_item.get('images', [])
                rep_image = next((img.get('vendorPath') or img.get('cdnPath') 
                                 for img in images if img.get('imageType') == 'REPRESENTATION'), "")
                if not rep_image and images:
                    rep_image = images[0].get('vendorPath') or images[0].get('cdnPath')

                detailed_products.append({
                    "상태": d.get('statusName', '수집완료'),
                    "원본상품명": d.get('sellerProductName', '상품명 없음'),
                    "AI최적화명": d.get('displayProductName', ''),
                    "원가": int(first_item.get('salePrice', 0)),
                    "판매가": int(first_item.get('salePrice', 0)),
                    "카테고리": d.get('productGroup', '쿠팡상품'),
                    "이미지URL": rep_image if str(rep_image).startswith('http') else f"https://{rep_image}" if rep_image else "",
                    "링크": f"https://www.coupang.com/vp/products/{d.get('productId', '')}"
                })
        
        print(f"✅ [LOG] 총 {len(detailed_products)}개 상품 가공 완료")
        print("="*50 + "\n")
        return detailed_products

    except Exception:
        traceback.print_exc()
        return []