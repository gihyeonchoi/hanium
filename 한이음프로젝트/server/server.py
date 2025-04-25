from flask import Flask, render_template, request, Response
from pishing_check import URL_parsing, URL_check, SSL_check, Domain_check, Location_to_IP
import json
import time
import csv
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze')
def analyze():
    query = request.args.get('query', '')
    urls = URL_parsing(query)
    log_file_path = "server_log.csv"
    client_ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    
    # CSV 파일 열기 (없으면 새로 생성)
    def open_csv():
        try:
            with open(log_file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                # 첫 번째 행만 읽어서 반환
                return list(reader)
        except FileNotFoundError:
            # 파일이 없으면 빈 리스트 반환
            return []

    def generate():
        # CSV 파일 작성
        with open(log_file_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            # 기존 CSV 파일의 첫 번째 행을 읽어서 존재 여부 확인
            existing_rows = open_csv()
            if len(existing_rows) == 0:
                # 파일이 비어있는 경우 첫 번째 데이터 전송 전에 헤더 추가
                writer.writerow(['Timestamp', 'IP', 'URL', 'URL_Check', 'SSL_Check', 'Domain_Days', 'Country'])

            yield f'data: {json.dumps({"type": "total", "total": len(urls)})}\n\n'
            for url in urls:
                yield f'data: {json.dumps({"type": "progress", "message": f"URL 검사 중... ({url})"})}\n\n'
                
                url_check = URL_check(url)
                yield f'data: {json.dumps({"type": "progress", "message": "✅ URL 대조 완료"})}\n\n'
                time.sleep(0.1)

                ssl_check = SSL_check(url)
                yield f'data: {json.dumps({"type": "progress", "message": "✅ SSL 인증서 검사 완료"})}\n\n'
                time.sleep(0.1)

                domain_days = Domain_check(url)
                yield f'data: {json.dumps({"type": "progress", "message": "✅ 도메인 생성일 확인 완료"})}\n\n'
                time.sleep(0.1)

                location_ok, country = Location_to_IP(url)
                yield f'data: {json.dumps({"type": "progress", "message": "✅ IP 위치 확인 완료"})}\n\n'
                time.sleep(0.1)

                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log_message = [timestamp, client_ip, url, url_check, ssl_check, domain_days, country]
                
                # CSV에 로그 기록
                writer.writerow(log_message)

                # 최종 결과 전송
                yield f'data: {json.dumps({"type": "result", "url": url, "url_check": url_check, "ssl_check": ssl_check, "domain_check": domain_days, "location_check": country})}\n\n'
                print("-----------------------------------------------------")

        # 모든 URL 검사 완료
        yield f'data: {json.dumps({"type": "done"})}\n\n'

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True)
