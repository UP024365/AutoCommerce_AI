import time
import hmac
import hashlib
import requests
import yaml

def test_coupang_final_fixed():
    # 1. 키 로드 (공백 제거)
    with open('config.yaml', 'r', encoding='utf-8') as f:
        keys = yaml.safe_load(f)
        ACCESS_KEY = keys.get('coupang_access_key', '').strip()
        SECRET_KEY = keys.get('coupang_secret_key', '').strip()
        VENDOR_ID = keys.get('coupang_vendor_id', '').strip()

    # 2. 경로 및 파라미터 설정
    method = "GET"
    path = "/v2/providers/seller_api/apis/api/v1/marketplace/seller-products"
    
    # [수정] 공식 문서 예제와 동일하게 vendorId를 첫 번째 파라미터로 배치
    query_str = f"vendorId={VENDOR_ID}&maxPerPage=1"
    
    # 3. 타임스탬프 (GMT)
    timestamp = time.strftime('%y%m%dT%H%M%SZ', time.gmtime())
    
    # 4. [중요] 서명 메시지 생성 (문서 공식: {timestamp}{method}{path}{query_string})
    # 경로와 쿼리 사이에 '?'를 넣지 않습니다.
    message = f"{timestamp}{method}{path}{query_str}"
    
    # 5. HMAC 서명 생성
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # 6. Authorization 헤더 구성 (콤마 뒤 공백 한 칸)
    authorization = (
        f"CEA algorithm=HmacSHA256, access-key={ACCESS_KEY}, "
        f"signed-date={timestamp}, signature={signature}"
    )
    
    headers = {
        "Content-type": "application/json;charset=UTF-8",
        "Authorization": authorization,
        "X-Requested-By": VENDOR_ID,
        "Connection": "close"
    }

    # 7. 실제 호출 URL (여기는 당연히 '?'가 필요합니다)
    url = f"https://api-gateway.coupang.com{path}?{query_str}"
    
    print(f"--- [최종 점검] ---")
    print(f"1. 서명 대상 메시지 (문서 기준): {message}")
    print(f"2. 전체 요청 URL: {url}")
    print("-" * 30)

    response = requests.get(url, headers=headers, timeout=10)
    print(f"응답 코드: {response.status_code}")
    print(f"응답 내용: {response.text}")

if __name__ == "__main__":
    test_coupang_final_fixed()