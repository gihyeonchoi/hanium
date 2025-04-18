import pandas as pd
import re

kor_net_original = pd.read_csv('all_subdomains_response.csv')
kor_net = kor_net_original[kor_net_original['Response Code'].notna()]
kor_net = kor_net[['W_Protocol']]

fishing_net_original = pd.read_csv('verified_online.csv')


def clean_url(url):
    # https:// 뒤의 첫 번째 / 이후 텍스트를 제거하는 정규식
    cleaned_url = re.sub(r'^(https://[^/]+).*', r'\1', url)
    return cleaned_url

# url 컬럼에 clean_url 함수 적용하여 새로운 'cleaned_url' 컬럼 생성
fishing_net_original['cleaned_url'] = fishing_net_original['url'].apply(clean_url)

# 'cleaned_url'만 포함된 새로운 DataFrame 생성
fishing_net = fishing_net_original[['cleaned_url']]