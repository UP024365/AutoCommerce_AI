import time
import os
import yaml
import streamlit as st
from openai import OpenAI

def load_api_key():
    """1순위: config.yaml, 2순위: st.secrets 확인"""
    if os.path.exists('config.yaml'):
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if config and 'openai_api_key' in config:
                return config['openai_api_key']
    
    if 'openai_api_key' in st.secrets:
        return st.secrets['openai_api_key']
        
    return None

def calculate_selling_price(supply_price, margin_rate=0.20, coupang_fee=0.10, extra_fee=0.0):
    """
    사촌님이 주신 마진 계산 공식 적용
    판매가 = 공급가 / (1 - 목표마진율 - 쿠팡수수료율 - 기타비용율)
    """
    try:
        # 분모가 0 이하가 되지 않도록 안전장치
        denominator = (1 - margin_rate - coupang_fee - extra_fee)
        if denominator <= 0:
            return supply_price * 1.5 # 계산 불가 시 최소 1.5배 설정
            
        selling_price = supply_price / denominator
        # 쿠팡은 보통 10원 단위로 끊으므로 10원 단위 반올림
        return int(round(selling_price, -1))
    except Exception:
        return int(supply_price * 1.3)

def refine_products_batch(product_list, margin_rate=0.20):
    """비용 최적화 일괄 가공 + 마진 계산 로직 통합"""
    
    # 1. 먼저 모든 상품의 판매가를 사촌님 공식으로 계산
    for p in product_list:
        supply_price = p.get('원가', 0)
        if supply_price > 0:
            p['판매가'] = calculate_selling_price(supply_price, margin_rate=margin_rate)
            # 마진액 계산 (참고용)
            p['예상수익'] = p['판매가'] - supply_price - (p['판매가'] * 0.1) # 판매가-원가-수수료

    # 2. AI 상품명 가공
    api_key = load_api_key()
    if not api_key:
        for p in product_list:
            p['AI최적화명'] = f"⚠️ [API키 미설정] {p['원본상품명'][:10]}"
        return

    client = OpenAI(api_key=api_key)
    raw_names = "\n".join([f"{i+1}. {p['원본상품명']}" for i, p in enumerate(product_list)])

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "너는 이커머스 상품명 가공 봇이야. 브랜드명과 핵심 기능 위주로 20자 이내로 다듬어. 결과만 한 줄에 하나씩 출력해."},
                {"role": "user", "content": f"가공할 상품명:\n{raw_names}"}
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        results = response.choices[0].message.content.strip().split('\n')
        for i, p in enumerate(product_list):
            if i < len(results):
                # '1. 상품명' 형태에서 상품명만 추출
                name = results[i].split('. ', 1)[-1] if '. ' in results[i] else results[i]
                p['AI최적화명'] = name.strip().replace('"', '')
                p['상태'] = "가공완료"
    except Exception as e:
        st.error(f"OpenAI 호출 실패: {e}")

def register_to_market(product):
    """
    실제 쿠팡 API 등록 전 시뮬레이션 로직
    (나중에 core/register.py의 함수로 교체될 예정)
    """
    if not product.get('AI최적화명') or product.get('판매가', 0) == 0:
        return False
        
    time.sleep(0.1) # API 통신 대기 시간 흉내
    product['상태'] = "등록완료"
    product['등록ID'] = f"CUP-{int(time.time())}"
    return True