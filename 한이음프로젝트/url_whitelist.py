# https://www.bugbountyclub.com/blog/view/14

import csv
# import pandas as pd
import requests
import certifi
import whois
import socket
from geoip import geolite2 # pip install python-geoip-python3
# https://pythonhosted.org/python-geoip/
from urllib.parse import urlparse

f = open('naver_subdomain_old.csv', 'r', encoding = 'utf-8')
rdr = csv.reader(f)

for line in rdr:
    print(line)


url = 'https://n.news.naver.com/mnews/article/009/0005462052'

parsed_url = urlparse(url)
base_url = parsed_url.scheme + "://" + parsed_url.netloc
# http:// 를 제외한 주소 얻기
# 실제 작동은 HTTP 없는 주소만 넣을것이기에 제외해야함


for i in rdr:
    if i[0] == parsed_url.netloc:
        print("찾음")
        break;
    else :
        print(f"{i} 아님")

url = 'https://google.com'
parsed_url = urlparse(url)
if parsed_url.scheme == "https":
    try:
        response = requests.get(url, verify=certifi.where())  # HTTPS에서는 SSL 인증서 검증
        print(f"SSL 인증서가 유효하고 연결이 성공적으로 이루어졌습니다. 상태 코드: {response.status_code}")
    except requests.exceptions.SSLError:
        print("SSL 인증서 오류 발생! SSL 인증서를 사용할 수 없거나 인증서가 유효하지 않습니다.")
else:
    print("이 URL은 HTTP 연결입니다. SSL 인증서 검증을 수행할 수 없습니다.")


# DATETIME 서버 시작 날자 확인
domain_info = whois.whois(url)
domain_info



# IP찾고 위치정보 찾기
def get_ip_from_url(url):
    try:
        # DNS 조회를 통해 IP 주소 반환
        ip_address = socket.gethostbyname(url)
        return ip_address
    except socket.gaierror:
        return None  # URL이 잘못되었거나 연결할 수 없을 때 None 반환

test = get_ip_from_url(parsed_url.netloc)
match = geolite2.lookup(test)

match
