import re
from urllib.parse import urlparse

text = """https://emsprd1.kyobobook.co.kr/0Ixc427922126"""

url_pattern = r'https?://[^\s]+'

# 찾기
urls = re.findall(url_pattern, text)

print(urls)

url = 'https://emsprd1.kyobobook.co.kr'
parsed_url = urlparse(url)
base_url = parsed_url.netloc

# url = 'naver.com'
import whois
# DATETIME 서버 시작 날자 확인
domain_info = whois.whois(url)
domain_info

from datetime import datetime

past_date = domain_info.creation_date
today = datetime.now()
years = today.year - past_date.year
if (today.month, today.day) < (past_date.month, past_date.day):
    years -= 1


a = today - past_date
a.days

print(f"{years}년 전에 만들어진 도메인입니다.")

domain_info = whois.whois(url)
day = datetime.now() - domain_info.creation_date

day.days




def Location_to_IP(url):
    '''
    URL을 받아 ISO 국가명을 리턴.
    리턴값 예시 : 0,1 = 비정상/정상 , {나라이름}
    '''
    import socket
    import geoip2.database
    import csv
    # GeoLite2 데이터베이스 로드
    country_reader = geoip2.database.Reader("GeoLite2-Country.mmdb")

    # IP 주소 얻기
    def get_ip_from_url(url):
        try:
            ip_address = socket.gethostbyname(url)
            return ip_address
        except socket.gaierror:
            return None

    # CSV 파일에서 ISO 코드 -> 한글 국가명 딕셔너리 만들기
    def load_country_dict(csv_file):
        iso_to_korean = {}
        with open(csv_file, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                korean_name = row['한글명']
                iso_code = row['2자리코드'].upper()
                iso_to_korean[iso_code] = korean_name
        return iso_to_korean

    try:
        parsed_url = urlparse(url)
        ip_address = get_ip_from_url(parsed_url.netloc)
        if ip_address is None:
            print("IP 주소를 찾을 수 없습니다.")
            return 0, "알수없음"
        
        # ISO 코드 가져오기
        country_response = country_reader.country(ip_address)
        iso_code = country_response.country.iso_code
        print("ISO 코드:", iso_code)

        # 한글 국가명 매핑
        country_dict = load_country_dict('ISO_code.csv')
        korean_name = country_dict.get(iso_code, "알 수 없음")
        print("국가명 (한글):", korean_name)
        return 1, korean_name

    except Exception as e:
        print("오류 발생:", e)
        return 0, "알수없음"
        

        
Location_to_IP(url)



import geoip2.database
country_reader = geoip2.database.Reader("GeoLite2-Country.mmdb")
country_response = country_reader.country('128.101.101.101')