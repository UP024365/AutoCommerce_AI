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
    vendor_id = keys.get('coupang_vendor_id')
    
    if not vendor_id:
        return {"returnCode": "ERROR", "returnMessage": "Vendor ID가 없습니다."}

    # 3. 쿠팡 요구 양식(JSON Payload) 구성
    # *주의: 실제 등록을 위해서는 카테고리ID, 이미지, 출고지 등 상세 정보가 더 필요하지만
    # 우선 가장 핵심적인 구조부터 잡습니다.
    payload = {
        "displayProductName": product.get('AI최적화명'),
        "sellerProductName": product.get('원본상품명'),
        "vendorId": vendor_id,
        "salePrice": product.get('판매가'),
        "displayCategoryCode": product.get('카테고리번호', 1001), # 예시: 일반 카테고리
        "deliveryMethod": "OTHERS", # 일반 택배 배송
        "deliveryCompanyCode": "CJGLS", # CJ대한통운 예시
        "deliveryChargeType": "FREE", # 무료배송 예시
        "outboundShippingPlaceCode": 1, # 등록된 출고지 번호
        "maximumBuyCount": 99,
        "items": [
            {
                "itemName": "단일옵션",
                "originalPrice": product.get('판매가'), # 원가 아님, 정가 개념
                "salePrice": product.get('판매가'),
                "maximumBuyCount": 99,
                "images": [
                    {
                        "imageOrder": 0,
                        "imageType": "REPRESENTATIVE", # 대표 이미지
                        "cdnPath": product.get('이미지URL', "http://example.com/image.jpg"),
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
                        "content": f"<div>{product.get('AI최적화명')} 상세설명</div>"
                    }
                ]
            }
        ]
    }

    # 4. 헤더 생성 (POST 메서드용)
    headers = generate_coupang_headers("POST", path)
    
    # 5. 실제 API 요청 전송
    url = f"https://api-gateway.coupang.com{path}"
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        result = response.json()
        
        # 성공 시 등록 정보 업데이트
        if result.get('returnCode') == "SUCCESS":
            product['상태'] = "등록완료"
            product['등록ID'] = result.get('data') # 쿠팡 상품 번호
        else:
            product['상태'] = "등록실패"
            
        return result
        
    except Exception as e:
        return {"returnCode": "ERROR", "returnMessage": str(e)}

def bulk_register_to_coupang(product_list):
    """
    여러 상품을 순차적으로 등록하는 함수
    """
    results = []
    for product in product_list:
        if product.get('상태') == "가공완료":
            res = register_product_to_coupang(product)
            results.append(res)
            time.sleep(0.1) # 쿠팡 API 초당 호출 제한(TPS) 준수
    return results