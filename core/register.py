import requests
import json
import time
from .collector import generate_coupang_headers, load_keys

def register_product_to_coupang(product):
    """
    가공된 상품 데이터를 쿠팡 API(POST)를 통해 실제 등록하는 함수
    """
    # 1. API 경로 설정
    path = "/v2/providers/seller_api/apis/api/v1/marketplace/seller-products"
    
    # 2. API 키 및 Vendor ID 로드
    keys = load_keys()
    vendor_id = str(keys.get('coupang_vendor_id', '')).strip()
    
    if not vendor_id:
        return {"returnCode": "ERROR", "returnMessage": "Vendor ID가 설정되지 않았습니다."}

    # 3. 쿠팡 요구 양식(JSON Payload) 구성
    # 필수 필드: 상품명, 카테고리, 이미지, 배송정보 등
    payload = {
        "displayProductName": product.get('AI최적화명') or product.get('원본상품명'),
        "sellerProductName": product.get('원본상품명'),
        "vendorId": vendor_id,
        "salePrice": product.get('판매가', product.get('원가', 0)),
        "displayCategoryCode": 1001,  # 임시: 실제 상품에 맞는 카테고리 번호로 교체 필요
        "deliveryMethod": "OTHERS", 
        "deliveryCompanyCode": "CJGLS",
        "deliveryChargeType": "FREE",
        "outboundShippingPlaceCode": 1, # 쿠팡 판매자 센터에 등록된 출고지 번호
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

    # 4. 헤더 생성 (POST 메서드, 쿼리 스트링 없음)
    headers = generate_coupang_headers("POST", path, "")
    
    # 5. 실제 API 요청 전송
    url = f"https://api-gateway.coupang.com{path}"
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        result = response.json()
        
        if response.status_code == 200 and result.get('returnCode') == "SUCCESS":
            product['상태'] = "등록완료"
            product['등록ID'] = result.get('data') 
        else:
            product['상태'] = "등록실패"
            
        return result
        
    except Exception as e:
        return {"returnCode": "ERROR", "returnMessage": str(e)}

def bulk_register_to_coupang(product_list):
    """
    여러 상품을 순차적으로 등록
    """
    results = []
    for product in product_list:
        # 가공완료 혹은 수집완료 상태인 상품만 등록 진행
        if product.get('상태') in ["가공완료", "수집완료", "승인완료"]:
            res = register_product_to_coupang(product)
            results.append(res)
            time.sleep(0.5) # 쿠팡 API 속도 제한 준수
    return results