from flask import Flask, render_template, request, Response
from pishing_check import URL_parsing, URL_check, SSL_check, Domain_check, Location_to_IP, Additional_risk
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
                print(f"컨트리 : {country}")
                yield f'data: {json.dumps({"type": "progress", "message": "✅ IP 위치 확인 완료"})}\n\n'
                time.sleep(0.1)

                additional_risk_score, additional_risk_msg = Additional_risk(url)

                yield f'data: {json.dumps({"type": "progress", "message": "✅ 추가 서버 정보 탐지 완료"})}\n\n'
                time.sleep(0.1)

                # 위험도 평가
                risk_score = 0
                risk_messages = []
                
                # 추가 서버 정보 평가
                if additional_risk_msg:
                    risk_score += additional_risk_score
                    risk_messages.extend(additional_risk_msg)
                    
                # URL 대조 결과 평가
                if not url_check:
                    risk_score += 20
                    risk_messages.append("데이터베이스에 등록되지 않은 도메인입니다.")
                
                # SSL 인증서 평가
                if ssl_check == 0:
                    risk_score += 25
                    risk_messages.append("SSL 인증서가 유효하지 않습니다.")
                elif ssl_check == -1:
                    risk_score += 15
                    risk_messages.append("HTTP 연결입니다. SSL 인증서가 존재하지 않습니다.")
                
                # 도메인 생성일 평가
                if 0 < domain_days < 120:
                    risk_score += 30
                    risk_messages.append(f"도메인이 최근({domain_days}일 전)에 생성되었습니다.")
                elif domain_days <= 0:
                    risk_score += 15
                    risk_messages.append("도메인 생성일을 확인할 수 없습니다.")
                
                # 서버 위치 평가
                if country not in ["대한민국", "한국", "알수없음"]:
                    risk_score += 15
                    risk_messages.append(f"서버가 해외({country})에 위치해 있습니다.")
                elif country == "알수없음":
                    risk_score += 20
                    risk_messages.append("서버 위치를 확인할 수 없습니다.")
                
                if not risk_messages:
                    risk_messages.append("해당 사이트는 안전합니다.")

                # 위험도 레벨 계산 (0-100)
                risk_level = min(100, risk_score)
                
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log_message = [timestamp, client_ip, url, url_check, ssl_check, domain_days, country]
                
                # CSV에 로그 기록
                writer.writerow(log_message)

                # 최종 결과 전송 (위험도 정보 포함)
                yield f'data: {json.dumps({"type": "result", "url": url, "url_check": url_check, "ssl_check": ssl_check, "domain_check": domain_days, "location_check": country, "risk_level": risk_level, "risk_messages": risk_messages})}\n\n'
                print("-----------------------------------------------------")

        # 모든 URL 검사 완료
        yield f'data: {json.dumps({"type": "done"})}\n\n'

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True)