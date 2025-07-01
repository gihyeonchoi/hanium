# https://www.bugbountyclub.com/blog/view/14

# import sys
# sys.executable
import csv
from urllib.parse import urlparse
import re

def URL_parsing(text):
    """
    메시지에서 URL만 추출 (스킴 없음, user@host 포함)
    - http, https 스킴
    - 스킴 없는 도메인
    - user@host 피싱 케이스
    """
    print(f"텍스트 : {text}")

    # 스킴 포함: http://, https://
    # user:pass@host 포맷도 포함되도록 [^\s]+
    scheme_pattern = r'https?://[^\s]+'

    # 스킴 없는 but user@host 피싱용: [domain]@[something]
    user_at_host_pattern = r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}@[^\s/]+'

    # 일반 스킴 없는 도메인 + 선택적 경로
    bare_domain_pattern = r'(?:www\.)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?'

    # 3개 패턴 조합
    url_pattern = f'({scheme_pattern}|{user_at_host_pattern}|{bare_domain_pattern})'

    urls = re.findall(url_pattern, text)
    urls = list(set(urls))  # 중복 제거

    print("검색한 URL:", urls)
    return urls

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
    - XSS 공격 패턴 탐지
    - Open Redirect 패턴 탐지
    
    리턴: 위험도 점수, 탐지된 위험 요소 메시지 리스트
    '''
    import re
    from urllib.parse import urlparse, parse_qs, unquote
    
    risk_messages = []
    risk_level = 0
    
    # URL 디코딩 (인코딩된 악성 패턴 탐지를 위해)
    decoded_url = unquote(url.lower())
    print(f"Additional_risk url : {url}")
    # 1. 기존 패턴 검사
    # 중간에 //가 1번 이상 반복되는 경우 (단, 시작의 https:// 제외)
    if url.count('//') > 1:
        risk_messages.append('🚨 URL에 비정상적인 리다이렉션 경로(//)가 포함되어 있습니다.')
        risk_level += 60
    
    # @ 기호 포함 여부
    if '@' in url:
        risk_messages.append('🚨 URL에 비정상적인 인증 우회(@)가 포함되어 있습니다.')
        risk_level += 60
    
    # 2. Open Redirect 패턴 검사
    open_redirect_params = [
        'url', 'redirect', 'return', 'next', 'goto', 'target', 'destination',
        'redir', 'redirect_url', 'return_url', 'go', 'out', 'link', 'continue',
        'site', 'view', 'to', 'ref', 'jump', 'jumpto', 'forward', 'dest'
    ]
    
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query.lower())
        
        for param in open_redirect_params:
            if param in params:
                param_value = params[param][0] if params[param] else ''
                # 외부 URL로 리다이렉트하는 패턴 검사
                if any(pattern in param_value for pattern in ['http://', 'https://', 'ftp://', '//']):
                    risk_messages.append(f'🚨 Open Redirect 취약점이 발견되었습니다 ({param})')
                    risk_level = 100  # Open Redirect는 매우 위험
                    break
    except:
        pass
    
    # 3. XSS 공격 패턴 검사
    xss_patterns = [
        r'<script[^>]*>',  # <script> 태그
        r'javascript:',     # javascript: 프로토콜
        r'onerror\s*=',    # onerror 이벤트
        r'onclick\s*=',    # onclick 이벤트
        r'onload\s*=',     # onload 이벤트
        r'onmouseover\s*=', # onmouseover 이벤트
        r'<iframe[^>]*>',  # iframe 태그
        r'<img[^>]*onerror', # img 태그와 onerror
        r'alert\s*\(',     # alert 함수
        r'eval\s*\(',      # eval 함수
        r'expression\s*\(', # CSS expression
        r'vbscript:',      # vbscript 프로토콜
        r'data:.*base64',  # data URL scheme
        r'<svg[^>]*onload', # SVG 태그
        r'&#x[0-9a-fA-F]+;', # 16진수 HTML 엔티티
        r'&#[0-9]+;',      # 10진수 HTML 엔티티
        r'document\.cookie', # 쿠키 접근
        r'window\.location', # 위치 변경
        r'<object[^>]*>',  # object 태그
        r'<embed[^>]*>',   # embed 태그
    ]
    
    for pattern in xss_patterns:
        if re.search(pattern, decoded_url, re.IGNORECASE):
            risk_messages.append(f'🚨 XSS 공격 패턴이 발견되었습니다: {pattern}')
            risk_level = 100  # XSS는 매우 위험
            break
    
    # 4. 동형 문자 공격 (Homograph Attack) 검사 - 키릴 문자 등
    # 영어처럼 보이지만 실제로는 다른 문자인 경우 탐지
    cyrillic_chars = {
        'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x',
        'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O', 
        'Р': 'P', 'С': 'C', 'Т': 'T', 'У': 'Y', 'Х': 'X'
    }
    
    # 그리스 문자
    greek_chars = {
        'α': 'a', 'ο': 'o', 'ν': 'v', 'τ': 't', 'ρ': 'p', 'μ': 'u',
        'Α': 'A', 'Β': 'B', 'Ε': 'E', 'Ζ': 'Z', 'Η': 'H', 'Ι': 'I', 
        'Κ': 'K', 'Μ': 'M', 'Ν': 'N', 'Ο': 'O', 'Ρ': 'P', 'Τ': 'T', 'Υ': 'Y', 'Χ': 'X'
    }
    
    # 기타 유사 문자 (라틴 확장 등)
    lookalike_chars = {
        'ɑ': 'a', 'ϲ': 'c', 'ԁ': 'd', 'ҽ': 'e', 'ց': 'g', 'һ': 'h', 'і': 'i',
        'ј': 'j', 'ӏ': 'l', 'ո': 'n', 'օ': 'o', 'ք': 'q', 'ѕ': 's', 'ս': 'u',
        'ѵ': 'v', 'ԝ': 'w', 'х': 'x', 'у': 'y', 'ᴢ': 'z'
    }
    
    # 도메인 부분 추출
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # 동형 문자 탐지
        homograph_found = False
        found_chars = []
        
        for char in domain:
            if char in cyrillic_chars:
                found_chars.append(f'{char}(키릴문자→{cyrillic_chars[char]})')
                homograph_found = True
            elif char in greek_chars:
                found_chars.append(f'{char}(그리스문자→{greek_chars[char]})')
                homograph_found = True
            elif char in lookalike_chars:
                found_chars.append(f'{char}(유사문자→{lookalike_chars[char]})')
                homograph_found = True
        
        if homograph_found:
            risk_messages.append(f'🚨 도메인에 영어로 위장한 문자가 포함되어 있습니다: {", ".join(found_chars[:3])}{"..." if len(found_chars) > 3 else ""}')
            risk_level = 100
    except:
        pass
    
    # 5. 추가 의심스러운 패턴 검사
    suspicious_patterns = [
        (r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', 'IP 주소가 직접 사용됨'),
        (r'(bit\.ly|tinyurl|goo\.gl|short\.link)', '단축 URL 서비스 사용'),
        (r'[0-9a-f]{32,}', '의심스러운 해시값 포함'),
        (r'\.tk|\.ml|\.ga|\.cf', '무료 도메인 사용'),
        (r'(%[0-9a-fA-F]{2}){5,}', '과도한 URL 인코딩'),
    ]
    
    for pattern, message in suspicious_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            risk_messages.append(f'⚠️ {message}')
            risk_level += 20
    
    # 6. 다중 리다이렉션 체인 검사
    redirect_count = len(re.findall(r'(https?://|ftp://|//)', decoded_url))
    if redirect_count > 2:  # 프로토콜 포함해서 2개 이상
        risk_messages.append(f'🚨 다중 리다이렉션이 감지되었습니다 ({redirect_count}개의 URL)')
        risk_level = 100
    
    # 위험도 최대값 제한
    risk_level = min(100, risk_level)
    
    # 위험도가 100인 경우 확정 메시지 추가
    if risk_level == 100 and not any('피싱 확정' in msg for msg in risk_messages):
        risk_messages.insert(0, '🚨 이 URL은 피싱 사이트일 가능성이 매우 높습니다!')
    
    return risk_level, risk_messages
