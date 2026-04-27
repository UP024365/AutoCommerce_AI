import requests
import json
import time
from .collector import generate_coupang_headers, load_keys

def register_product_to_coupang(product):
    """
    쿠팡 상품 생성 API (POST) 호출 및 상세 로그 출력
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
        "outboundShippingPlaceCode": keys.get('outbound_code', 1), # config.yaml의 출고지 번호
        "vendorInventoryCode": f"INV-{int(time.time())}", 
        "maximumBuyCount": 99,
        "items": [
            {
                "itemName": "단일상품",
                "originalPrice": product.get('판매가', product.get('원가', 0)),
                "salePrice": product.get('판매가', product.get('원가', 0)),
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
        # 타임아웃을 15초로 늘려 안정성 확보
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)
        
        # JSON 변환 시도 전 상태 코드 확인
        try:
            result = response.json()
        except Exception:
            result = {"returnCode": "ERROR", "returnMessage": f"JSON 파싱 실패: {response.text}"}

        # --- 상세 디버깅 로그 (터미널에서 확인 가능) ---
        print(f"\n--- [쿠팡 API 전송 로그] ---")
        print(f"상품명: {payload['displayProductName']}")
        print(f"HTTP 상태 코드: {response.status_code}")
        print(f"전체 응답 본문: {json.dumps(result, indent=2, ensure_ascii=False)}")
        print("-" * 30 + "\n")

        if response.status_code == 200 and result.get('returnCode') == "SUCCESS":
            product['상태'] = "승인대기" 
            product['sellerProductId'] = result.get('data')
        else:
            # 에러 메시지가 없을 경우 HTTP 코드로 대체
            if not result.get('returnMessage'):
                result['returnMessage'] = f"HTTP {response.status_code} 오류 (사유 미반환)"
            product['상태'] = "등록실패"
            
        return result
        
    except Exception as e:
        error_msg = f"네트워크/시스템 오류: {str(e)}"
        print(f"🚨 예외 발생: {error_msg}")
        return {"returnCode": "ERROR", "returnMessage": error_msg}

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
    # 실제 구현 시 상품 수정 API를 통해 '판매중지' 상태로 업데이트 필요
    time.sleep(0.2)
    return True

def bulk_register_to_coupang(product_list):
    """일괄 등록 및 결과 리스트 반환"""
    results = []
    for product in product_list:
        # '등록완료'가 아닌 상품들만 대상으로 시도
        if product.get('상태') != "등록완료":
            res = register_product_to_coupang(product)
            results.append(res)
            time.sleep(0.5) # 초당 호출 제한 준수
    return results