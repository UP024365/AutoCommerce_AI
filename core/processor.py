import time
import os
import yaml
import streamlit as st
from openai import OpenAI

def load_api_key():
    if os.path.exists('config.yaml'):
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if config and 'openai_api_key' in config:
                return config['openai_api_key']
    if 'openai_api_key' in st.secrets:
        return st.secrets['openai_api_key']
    return None

def calculate_selling_price(supply_price, margin_rate=0.20, coupang_fee=0.10, tax_rate=0.10):
    """
    공식: 공급가 / (1 - 마진율 - 수수료율 - 부가세율)
    """
    try:
        # 분모가 0이 되는 것을 방지
        denominator = 1 - margin_rate - coupang_fee - tax_rate
        if denominator <= 0:
            return supply_price * 1.5 # 방어 코드: 마진 설정 오류 시 1.5배 적용
        
        calculated_price = supply_price / denominator
        # 10원 단위 반올림 (쿠팡 등록 규격 권장)
        return int(round(calculated_price, -1))
    except Exception:
        return supply_price * 1.3

def refine_products_batch(product_list):
    """AI 상품명 최적화 및 기본 가격 책정 로직 통합"""
    api_key = load_api_key()
    
    # 1. AI 이름 가공
    if api_key:
        client = OpenAI(api_key=api_key)
        raw_names = "\n".join([f"{i+1}. {p['원본상품명']}" for i, p in enumerate(product_list)])
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "너는 이커머스 상품명 가공 봇이야. 다른 설명 없이 결과만 한 줄에 하나씩 출력해."},
                    {"role": "user", "content": f"20자 이내 쇼핑몰 이름으로 가공:\n{raw_names}"}
                ],
                max_tokens=300,
                temperature=0.3
            )
            results = response.choices[0].message.content.strip().split('\n')
        except Exception as e:
            st.error(f"OpenAI 호출 실패: {e}")
            results = []
    else:
        results = []

    # 2. 데이터 업데이트 및 가격 산출
    for i, p in enumerate(product_list):
        if results and i < len(results):
            name = results[i].split('. ')[-1] if '. ' in results[i] else results[i]
            p['AI최적화명'] = name.strip().replace('"', '')
        
        # 기본 마진 20%, 수수료 10%, 부가세 10% 가정하여 초기 판매가 세팅
        p['판매가'] = calculate_selling_price(p['원가'])
        p['상태'] = "가공완료"