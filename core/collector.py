import requests
import yaml
import hmac
import hashlib
from datetime import datetime
import traceback

def load_keys():
    """config.yaml에서 API 키 로드"""
    with open('config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def generate_coupang_headers(method, path, query_str):
    """쿠팡 HMAC 서명 헤더 생성"""
    keys = load_keys()
    access_key = keys['coupang_access_key']
    secret_key = keys['coupang_secret_key']
    
    timestamp = datetime.utcnow().strftime('%y%m%dT%H%M%SZ')
    message = timestamp + method + path + query_str
    
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return {
        "Content-Type": "application/json",
        "Authorization": f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={timestamp}, signature={signature}"
    }

def fetch_real_naver_products(keyword, display_count=10):
    """네이버 쇼핑 검색"""
    keys = load_keys()
    url = f"https://openapi.naver.com/v1/search/shop.json?query={keyword}&display={display_count}"
    headers = {
        "X-Naver-Client-Id": keys['naver_client_id'],
        "X-Naver-Client-Secret": keys['naver_client_secret']
    }
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
    return []

def fetch_coupang_products(max_results=10):
    """쿠팡 내 상품 상세 정보 수집 (상세 로그 포함)"""
    print("\n" + "="*50)
    print("🚀 [LOG] 쿠팡 상품 수집 시도 중...")
    try:
        keys = load_keys()
        vendor_id = keys.get('coupang_vendor_id')
        
        # 1. 상품 목록 조회
        list_path = "/v2/providers/seller_api/apis/api/v1/marketplace/seller-products"
        list_query = f"vendorId={vendor_id}&maxPerPage={max_results}"
        list_url = f"https://api-gateway.coupang.com{list_path}?{list_query}"
        
        headers = generate_coupang_headers("GET", list_path, list_query)
        response = requests.get(list_url, headers=headers, timeout=10)
        
        print(f"📡 [LOG] 목록 조회 결과 코드: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ [LOG] 에러 내용: {response.text}")
            return []

        summary_data = response.json().get('data', [])
        detailed_products = []

        # 2. 각 상품 ID별 상세 조회
        for summary in summary_data:
            sp_id = summary.get('sellerProductId')
            detail_path = f"/v2/providers/seller_api/apis/api/v1/marketplace/seller-products/{sp_id}"
            detail_headers = generate_coupang_headers("GET", detail_path, "")
            detail_res = requests.get(f"https://api-gateway.coupang.com{detail_path}", headers=detail_headers, timeout=10)
            
            if detail_res.status_code == 200:
                res_json = detail_res.json()
                d = res_json.get('data', {})
                items = d.get('items', [])
                first_item = items[0] if items else {}
                
                # 이미지 추출 (REPRESENTATION 우선)
                images = first_item.get('images', [])
                rep_image = ""
                for img in images:
                    if img.get('imageType') == 'REPRESENTATION':
                        rep_image = img.get('vendorPath') or img.get('cdnPath')
                        break
                if not rep_image and images: # 대표이미지 없을 시 첫 번째 이미지
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

    except Exception as e:
        print(f"🚨 [LOG] 실행 중 예외 발생")
        traceback.print_exc()
        return []