import requests
import json
import time
from .collector import generate_coupang_headers, load_keys

def register_product_to_coupang(product):
    """
    쿠팡 상품 생성 API (POST) 호출
    참고: https://developers.coupangcorp.com/hc/ko/articles/360033877853
    """
    path = "/v2/providers/seller_api/apis/api/v1/marketplace/seller-products"
    keys = load_keys()
    vendor_id = str(keys.get('coupang_vendor_id', '')).strip()
    
    if not vendor_id:
        return {"returnCode": "ERROR", "returnMessage": "Vendor ID가 설정되지 않았습니다."}

    # 쿠팡 API 필수 규격 데이터 구성
    payload = {
        "displayProductName": product.get('AI최적화명') or product.get('원본상품명'),
        "sellerProductName": product.get('원본상품명'),
        "vendorId": vendor_id,
        "displayCategoryCode": int(product.get('카테고리', 1001)),
        "deliveryMethod": "OTHERS", 
        "deliveryCompanyCode": "CJGLS",
        "deliveryChargeType": "FREE",
        "outboundShippingPlaceCode": keys.get('outbound_code', 1), # 출고지 번호
        "vendorInventoryCode": f"INV-{int(time.time())}", # 자체 관리 코드
        "maximumBuyCount": 99,
        "items": [
            {
                "itemName": "단일상품",
                "originalPrice": product.get('판매가', 0),
                "salePrice": product.get('판매가', 0),
                "maximumBuyCount": 99,
                "images": [
                    {
                        "imageOrder": 0,
                        "imageType": "REPRESENTATIVE",
                        "vendorPath": product.get('이미지URL')
                    }
                ],
                "notices": [
                    {
                        "noticeCategoryName": "기타 재화",
                        "noticeCategoryDetailName": "상세페이지 참조",
                        "content": "상세페이지 참조"
                    }
                ],
                "attributes": [],
                "contents": [
                    {
                        "contentsType": "HTML",
                        "content": f"<div><img src='{product.get('이미지URL')}'></div>"
                    }
                ]
            }
        ]
    }

    headers = generate_coupang_headers("POST", path, "")
    url = f"https://api-gateway.coupang.com{path}"
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        result = response.json()
        
        # 성공 시 '상태'를 승인대기로 변경
        if response.status_code == 200 and result.get('returnCode') == "SUCCESS":
            product['상태'] = "승인대기" 
            product['sellerProductId'] = result.get('data') # 생성된 상품 ID 저장
        return result
    except Exception as e:
        return {"returnCode": "ERROR", "returnMessage": str(e)}

def get_registered_products():
    """등록된 상품 목록 및 승인 상태 조회 (GET)"""
    keys = load_keys()
    vendor_id = str(keys.get('coupang_vendor_id', '')).strip()
    path = "/v2/providers/seller_api/apis/api/v1/marketplace/seller-products"
    query = f"vendorId={vendor_id}&maxPerPage=50"
    
    headers = generate_coupang_headers("GET", path, query)
    url = f"https://api-gateway.coupang.com{path}?{query}"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('data', [])
        return []
    except Exception:
        return []

def stop_selling_product(seller_product_id):
    """판매 중지 처리"""
    # 실제로는 승인 상태 변경 API를 사용하여 'SUSPENDED'로 변경해야 함
    time.sleep(0.2)
    return True

def bulk_register_to_coupang(product_list):
    results = []
    for product in product_list:
        res = register_product_to_coupang(product)
        results.append(res)
        time.sleep(0.5) 
    return results