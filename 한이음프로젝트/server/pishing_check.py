# https://www.bugbountyclub.com/blog/view/14

# import sys
# sys.executable
import csv
from urllib.parse import urlparse

def URL_parsing(text):
    '''
    메시지를 가져와 url만 파싱. list로 리턴
    - http, https 포함된 URL
    - www. 또는 스킴 없는 도메인 (예: naver.com)
    '''
    import re

    # http(s):// 로 시작하는 것 + www. 또는 도메인 형태도 추출
    url_pattern = r'(https?://[^\s]+|(?:www\.)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)'
    
    urls = re.findall(url_pattern, text)
    print("검색한 url :", urls)
    return list(set(urls))  # 중복 제거


def URL_check(url):
    '''
    URL을 받아 도메인 DB와 대조. Bool 리턴. URL은 String 으로
    www. 여부 관계없이 매칭 시 True
    '''
    import csv
    from urllib.parse import urlparse

    def get_base_domain(u):
        parsed = urlparse(u)
        return parsed.netloc.lower() if parsed.netloc else parsed.path.lower()

    # DB 불러오기
    with open('../domains_data/all_subdomains_response.csv', 'r', encoding='utf-8') as f:
        rdr = csv.reader(f)
        db_domains = set(row[0].lower() for row in rdr if row)

    urls_to_try = []

    # 스킴이 있는 경우는 그대로
    if url.startswith(('http://', 'https://')):
        urls_to_try.append(url)
    else:
        # 스킴이 없는 경우 https → http 순으로 시도
        urls_to_try.append('https://' + url)
        urls_to_try.append('http://' + url)

    for try_url in urls_to_try:
        base_url = get_base_domain(try_url)

        url_variants = {base_url}
        if base_url.startswith("www."):
            url_variants.add(base_url[4:])
        else:
            url_variants.add("www." + base_url)

        print(f"▶ 시도 중: {try_url} → 도메인 변형: {url_variants}")

        for variant in url_variants:
            if variant in db_domains:
                print(f"✅ URL_check: {variant} 찾음")
                return True

    print(f"❌ URL_check: 모든 프로토콜 시도 실패 - {url}")
    return False



def SSL_check(url): 
    '''
    URL을 받아 SSL 인증서 비교.
    - 1 = 정상 (SSL 인증서 유효)
    - 0 = 비정상 (SSL 오류)
    - -1 = HTTP 연결 (SSL 없음)
    - -2 = 연결 실패 (도메인 없음, 연결 거부 등)
    '''
    import requests
    import certifi
    from urllib.parse import urlparse

    print(f"ssl 체크 : {url}")

    def try_request(full_url):
        try:
            response = requests.get(full_url, verify=certifi.where(), timeout=5)
            print(f"[성공] {full_url} 연결됨 (status: {response.status_code})")
            return 1  # SSL 인증 성공
        except requests.exceptions.SSLError:
            print(f"[SSL 오류] {full_url}")
            return 0  # SSL 인증 실패
        except requests.exceptions.RequestException as e:
            print(f"[요청 실패] {full_url} - {e}")
            return -2  # 연결 실패

    parsed = urlparse(url)
    # 스킴이 없다면 https 먼저 붙여서 시도
    if not parsed.scheme:
        https_url = "https://" + url
        result = try_request(https_url)
        if result == -2:  # https 실패하면 http도 시도
            http_url = "http://" + url
            print(f"https 실패, http 시도 중: {http_url}")
            return -1 if try_request(http_url) == 1 else -2
        else:
            return result

    # 스킴이 명시된 경우 그대로 시도
    if parsed.scheme == "https":
        return try_request(url)
    elif parsed.scheme == "http":
        print("HTTP URL입니다. SSL 인증서가 존재하지 않습니다.")
        return -1
    else:
        print(f"[오류] 지원하지 않는 스킴: {parsed.scheme}")
        return -2



def Domain_check(url):
    '''
    URL을 받아 생성된 날짜와 현재 날짜 차이를 일(day)로 리턴.
    '''
    from datetime import datetime
    import whois

    try:
        domain_info = whois.whois(url)
        creation_date = domain_info.creation_date

        # 리스트로 올 경우 첫 번째 값 사용
        if isinstance(creation_date, list):
            creation_date = creation_date[0]

        if creation_date is None:
            print("도메인 생성일 정보를 찾을 수 없습니다.")
            return -1  # 혹은 None

        day = datetime.now() - creation_date
        return day.days

    except Exception as e:
        print(f"Domain_check 오류: {e}")
        return -1  # 오류 시 -1 반환




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

    print(f"로케이션 아이피 : {url}")
    try:
        parsed_url = urlparse(url)
        print(parsed_url)
        ip_address = get_ip_from_url(parsed_url.netloc if parsed_url.netloc else parsed_url.path)
        if ip_address is None:
            print("IP 주소를 찾을 수 없습니다.")
            return False, "알수없음"
        
        # ISO 코드 가져오기
        country_response = country_reader.country(ip_address)
        print("country_response : ", country_response)
        iso_code = (country_response.registered_country.iso_code or "").upper()
        print(f"[Location] ISO 코드: {iso_code}")


        # 한글 국가명 매핑
        country_dict = load_country_dict('../ISO_code.csv')
        korean_name = country_dict.get(iso_code, "알 수 없음")
        print("국가명 (한글):", korean_name)
        return True, korean_name

    except Exception as e:
        print("오류 발생:", e)
        return False, "알수없음"
    
def Additional_risk(url):
    '''
    URL 문자열에서 추가적인 위험 요소 탐지
    - "//"가 URL 경로 중간에 여러 번 등장할 경우
    - "@" 심볼이 포함된 경우 (피싱 URL에 종종 사용됨)
    
    리턴: 탐지된 위험 요소 메시지 리스트
    '''
    risk_messages = []
    risk_level = 0

    # 중간에 //가 1번 이상 반복되는 경우 (단, 시작의 https:// 제외)
    if url.count('//') > 1:
        risk_messages.append('⚠️ URL에 비정상적인 리다이렉션 경로가 포함되어 있습니다.')
        risk_level += 40
        

    # @ 기호 포함 여부
    if '@' in url:
        risk_messages.append('⚠️ URL에 비정상적인 서버 정보(@심볼)가 포함되어 있습니다.')
        risk_level += 40

    return risk_level, risk_messages
