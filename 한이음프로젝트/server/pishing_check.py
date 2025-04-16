# https://www.bugbountyclub.com/blog/view/14

# import sys
# sys.executable
import csv
from urllib.parse import urlparse

def URL_parsing(text):
    '''
    메시지를 가져와 url만 파싱. list로 리턴
    '''
    import re
    url_pattern = r'https?://[^\s]+'
    url = re.findall(url_pattern, text)

    return url if url else []


def URL_check(url):
    '''
    URL을 받아 도메인 DB와 대조. Bool 리턴. URL은 String 으로
    '''
    f = open('../domains_data/all_subdomains_response.csv', 'r', encoding = 'utf-8')
    rdr = csv.reader(f)

    parsed_url = urlparse(url)

    ## url 합치기 (http.... 로 시작)
    # base_url = parsed_url.scheme + "://" + parsed_url.netloc
    ## 도메인정보만 (naver.com 이런거만)
    base_url = parsed_url.netloc

    for i in rdr:
        if i[0] == base_url:
            print(f"URL_check : {base_url} 찾음")
            return True
    print(f"URL_check : {base_url} 찾지못함")
    return False


def SSL_check(url):
    '''
    URL을 받아 SSL 인증서 비교. 1 = 정상 / 0 = 비정상 / -1 = HTTP 연결
    '''
    import requests
    import certifi

    parsed_url = urlparse(url)
    if parsed_url.scheme == "https":
        try:
            response = requests.get(url, verify=certifi.where())  # HTTPS에서는 SSL 인증서 검증
            print(f"SSL 인증서가 유효하고 연결이 성공적으로 이루어졌습니다. 상태 코드: {response.status_code}")
            return 1
        except requests.exceptions.SSLError:
            print("SSL 인증서 오류 발생! SSL 인증서를 사용할 수 없거나 인증서가 유효하지 않습니다.")
            return 0
    else:
        print("이 URL은 HTTP 연결입니다. SSL 인증서 검증을 수행할 수 없습니다.")
        return -1


def Domain_check(url):
    '''
    URL을 받아 날짜(day)를 리턴.
    예 : 1997년 - 2025년 = 대략 10000(일) 리턴
    '''
    from datetime import datetime
    import whois
    # DATETIME 서버 시작 날자 확인
    domain_info = whois.whois(url)
    day = datetime.now() - domain_info.creation_date

    return day.days



def Location_to_IP(url):
    '''
    URL을 받아 ISO 국가명을 리턴.
    리턴값 2개 예시 : 정상비정상 bool , 나라이름 string
    '''
    import socket
    import geoip2.database
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
            return False, "알수없음"
        
        # ISO 코드 가져오기
        country_response = country_reader.country(ip_address)
        iso_code = country_response.country.iso_code
        print("ISO 코드:", iso_code)

        # 한글 국가명 매핑
        country_dict = load_country_dict('../ISO_code.csv')
        korean_name = country_dict.get(iso_code, "알 수 없음")
        print("국가명 (한글):", korean_name)
        return True, korean_name

    except Exception as e:
        print("오류 발생:", e)
        return False, "알수없음"