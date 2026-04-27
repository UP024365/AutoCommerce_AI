import os
import time
import hmac
import hashlib
import requests
import yaml
import traceback
import streamlit as st  # 스트림릿 클라우드 Secrets 사용을 위해 추가

# [공식 예제 핵심] 시스템 타임존을 GMT로 설정하여 시간 오차 방지
os.environ['TZ'] = 'GMT+0'

def load_keys():
    """
    1순위: 스트림릿 클라우드 Secrets 확인 (배포 환경)
    2순위: config.yaml 확인 (로컬 환경)
    """
    # 1. 스트림릿 클라우드 Secrets 확인
    try:
        # Secrets에 naver_client_id가 등록되어 있는지 확인
        if "naver_client_id" in st.secrets:
            return {
                'naver_client_id': st.secrets["naver_client_id"],
                'naver_client_secret': st.secrets["naver_client_secret"],
                'openai_api_key': st.secrets["openai_api_key"],
                'coupang_access_key': st.secrets["coupang_access_key"],
                'coupang_secret_key': st.secrets["coupang_secret_key"],
                'coupang_vendor_id': st.secrets["coupang_vendor_id"]
            }
    except Exception:
        # st.secrets 접근 실패 시(로컬 등) 통과
        pass

    # 2. 로컬 config.yaml 확인
    try:
        if os.path.exists('config.yaml'):
            with open('config.yaml', 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
    except Exception:
        traceback.print_exc()
        
    return {}

def generate_coupang_headers(method, path, query_str=""):
    """쿠팡 공식 예제 로직을 구현한 헤더 생성 함수"""
    keys = load_keys()
    access_key = keys.get('coupang_access_key', '').strip()
    secret_key = keys.get('coupang_secret_key', '').strip()
    
    # GMT 기준 타임스탬프 생성
    timestamp = time.strftime('%y%m%dT%H%M%SZ', time.gmtime())
    
    # [공식 예제 방식] 서명 메시지 구성 시 경로와 쿼리 사이 '?' 제외
    clean_query = query_str.replace('?', '').strip()
    message = timestamp + method + path + clean_query
    
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return {
        "Content-type": "application/json;charset=UTF-8",
        "Authorization": f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={timestamp}, signature={signature}"
    }

def fetch_real_naver_products(keyword, display_count=10, start=1):
    """
    네이버 쇼핑 검색 (중복 방지를 위해 start 파라미터 추가)
    start: 검색 시작 위치 (최대 1000)
    """
    keys = load_keys()
    url = f"https://openapi.naver.com/v1/search/shop.json?query={keyword}&display={display_count}&start={start}"
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
    """쿠팡 내 상품 수집 (공식 문서 기반 필터링 적용)"""
    print("\n" + "="*50)
    print("🚀 [LOG] 쿠팡 상품 수집 시도 중...")
    try:
        keys = load_keys()
        vendor_id = str(keys.get('coupang_vendor_id', '')).strip()
        
        if not vendor_id:
            print("❌ [LOG] Vendor ID가 설정되지 않았습니다.")
            return []

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
        
        if not summary_data:
            print("⚠️ [LOG] 등록된 상품이 없습니다. (현재 상태에서 data: [] 반환됨)")
            return []

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
                
                # 이미지 추출 (REPRESENTATION 우선)
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