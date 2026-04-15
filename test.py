import requests
import json

# 1. 발급받은 키 설정
client_id = "Oo972SztuDkUXxrFP7AB"
client_secret = "7bCnRE_Cq6"

# 2. API 엔드포인트 (쇼핑인사이트 - 카테고리별 클릭 추이)
url = "https://openapi.naver.com/v1/datalab/shopping/categories"

# 3. 요청 데이터 (예: 디지털/가전 카테고리의 트렌드 확인)
body = {
    "startDate": "2026-04-01",
    "endDate": "2026-04-14",
    "timeUnit": "date",
    "category": [
        {"name": "디지털/가전", "param": ["50000003"]} # 50000003는 가전 카테고리 번호
    ],
    "device": "pc", # pc/mo 선택 가능
    "gender": "",   # 전체
    "ages": []      # 전체 연령대
}

headers = {
    "X-Naver-Client-Id": client_id,
    "X-Naver-Client-Secret": client_secret,
    "Content-Type": "application/json"
}

# 4. API 호출
response = requests.post(url, headers=headers, data=json.dumps(body))

# 5. 결과 확인
if response.status_code == 200:
    res_data = response.json()
    print("✅ 연결 성공!")
    print(json.dumps(res_data, indent=4, ensure_ascii=False))
else:
    print(f"❌ 에러 발생: {response.status_code}")
    print(response.text)