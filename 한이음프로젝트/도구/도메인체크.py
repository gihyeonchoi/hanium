import requests
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import urllib3
import urllib.parse
import idna

# 도메인 목록을 저장한 텍스트 파일 경로
input_file = '../domains_data/all_subdomains.txt'
output_file = '../domains_data/all_subdomains_response.csv'

# 도메인 상태 체크 함수
def check_website_status(raw_domain):
    try:
        # http:// 없이 들어오는 걸 대비해서 url 생성
        parsed = urllib.parse.urlparse(raw_domain if "://" in raw_domain else "http://" + raw_domain)
        
        # 도메인 인코딩 (한글 포함 안전하게 처리)
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Invalid hostname")

        try:
            encoded_host = idna.encode(hostname).decode("ascii")
        except idna.IDNAError:
            return raw_domain, "IDNA Encoding Error", None, "http://"

        encoded_url = parsed._replace(netloc=encoded_host).geturl()

        response = requests.get(encoded_url, timeout=(5, 7), allow_redirects=True)
        final_url = response.url
        protocol = "https://" if final_url.startswith("https://") else "http://"
        return encoded_url, "Success", response.status_code, protocol

    except requests.exceptions.TooManyRedirects:
        return raw_domain, "Too Many Redirects", None, "http://"
    except requests.exceptions.Timeout:
        return raw_domain, "Timeout", None, "http://"
    except requests.exceptions.ConnectionError:
        return raw_domain, "Connection Error", None, "http://"
    except urllib3.exceptions.LocationParseError:
        return raw_domain, "URL Parse Error", None, "http://"
    except UnicodeError:
        return raw_domain, "Unicode Error", None, "http://"
    except Exception as e:
        print(f"[오류] {raw_domain} 에서 예외 발생: {e}")
        return raw_domain, f"Unhandled Error: {e}", None, "http://"

# 도메인 목록을 처리하고 CSV 파일로 저장
def process_domains(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as file:
        domains = [line.strip() for line in file if line.strip()]

    with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Domain', 'W_Protocol', 'Status', 'Response Code']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = {executor.submit(check_website_status, domain): domain for domain in domains}
            with tqdm(total=len(domains), desc="Processing domains", unit="domain") as pbar:
                for future in as_completed(futures):
                    domain, status, response_code, protocol = future.result()
                    domain_cleaned = domain.replace("http://", "").replace("https://", "")
                    writer.writerow({
                        'Domain': domain_cleaned,
                        'W_Protocol': protocol + domain_cleaned,
                        'Status': status,
                        'Response Code': response_code if response_code else 'N/A'
                    })
                    pbar.update(1)

process_domains(input_file, output_file)
print(f"\n도메인 상태 체크가 완료되었습니다. 결과는 {output_file} 파일에 저장되었습니다.")
