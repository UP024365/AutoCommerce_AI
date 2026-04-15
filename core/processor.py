import time
import os
import yaml
import streamlit as st
from openai import OpenAI

def load_api_key():
    """
    1순위: config.yaml 확인
    2순위: st.secrets 확인
    """
    # 1. config.yaml 확인
    if os.path.exists('config.yaml'):
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if config and 'openai_api_key' in config:
                return config['openai_api_key']
    
    # 2. st.secrets 확인 (클라우드 배포용)
    if 'openai_api_key' in st.secrets:
        return st.secrets['openai_api_key']
        
    return None

def refine_products_batch(product_list):
    """비용 최적화 일괄 가공"""
    api_key = load_api_key()
    
    if not api_key:
        # 키가 없을 때 안내 문구
        for p in product_list:
            p['AI최적화명'] = f"⚠️ [API키 미설정] {p['원본상품명'][:10]}"
        return

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
        for i, p in enumerate(product_list):
            if i < len(results):
                name = results[i].split('. ')[-1] if '. ' in results[i] else results[i]
                p['AI최적화명'] = name.strip().replace('"', '')
                p['상태'] = "가공완료"
    except Exception as e:
        st.error(f"OpenAI 호출 실패: {e}")

def register_to_market(product):
    """마켓 등록 로직"""
    time.sleep(0.2)
    product['상태'] = "등록완료"
    product['등록ID'] = f"CUP-{int(time.time())}"
    return True