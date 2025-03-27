import requests
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# 도메인 목록을 저장한 텍스트 파일 경로
input_file = 'naver_subdomain.txt'
# 결과를 저장할 CSV 파일 경로
output_file = 'naver_subdomain.csv'

# 도메인 상태 체크 함수
def check_website_status(url):
    try:
        # 리디렉션을 추적하여 최종 URL을 확인합니다.
        response = requests.get(url, timeout=7, allow_redirects=True)
        
        # 최종 URL이 https://로 시작하는지 확인
        final_url = response.url
        
        # 최종 URL이 https://로 시작하면 https로 저장, 그렇지 않으면 http로 저장
        if final_url.startswith("https://"):
            return url, "Success", response.status_code, "https://"
        else:
            return url, "Success", response.status_code, "http://"
    
    except requests.exceptions.Timeout:
        return url, "Timeout", None, "http://"  # 타임아웃 처리
    except requests.exceptions.ConnectionError:
        return url, "Connection Error", None, "http://"  # 연결 오류 처리
    except requests.exceptions.RequestException as e:
        return url, f"Request Error: {e}", None, "http://"  # 다른 요청 오류 처리

# 도메인 목록을 텍스트 파일에서 읽어서 상태 체크 후 CSV 파일로 저장
def process_domains(input_file, output_file):
    # 도메인 목록을 텍스트 파일에서 읽기
    with open(input_file, 'r') as file:
        domains = [line.strip() for line in file.readlines() if line.strip()]

    # CSV 파일을 열어서 헤더 작성
    with open(output_file, mode='w', newline='') as csvfile:
        fieldnames = ['Domain', 'W_Protocol', 'Status', 'Response Code']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()  # 헤더 작성
        
        # 스레드 풀 생성
        with ThreadPoolExecutor(max_workers=16) as executor:
            # tqdm을 사용하여 진행상황 표시
            futures = {executor.submit(check_website_status, f'http://{domain}'): domain for domain in domains}
            total_domains = len(domains)  # 총 도메인 수

            # 진행 상태 표시
            with tqdm(total=total_domains, desc="Processing domains", unit="domain") as pbar:
                for future in as_completed(futures):
                    domain, status, response_code, protocol = future.result()
                    
                    # 'http://' 또는 'https://'를 제외한 도메인만 기록
                    domain_without_http = domain.replace("http://", "").replace("https://", "")
                    
                    # CSV에 결과 기록
                    writer.writerow({
                        'Domain': domain_without_http,
                        'W_Protocol': protocol + domain_without_http,
                        'Status': status,
                        'Response Code': response_code if response_code else 'N/A'
                    })
                    pbar.update(1)  # 한 도메인씩 처리할 때마다 진행 상태 업데이트

# 도메인 목록을 처리하고 CSV 파일로 저장
process_domains(input_file, output_file)

print(f"\n도메인 상태 체크가 완료되었습니다. 결과는 {output_file} 파일에 저장되었습니다.")
