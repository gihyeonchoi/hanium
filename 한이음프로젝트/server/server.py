from flask import Flask, render_template, request, Response
from pishing_check import URL_parsing, URL_check, SSL_check, Domain_check, Location_to_IP
import json
import time

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze')
def analyze():
    query = request.args.get('query', '')
    urls = URL_parsing(query)

    def generate():
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

            # 최종 결과 전송
            yield f'data: {json.dumps({"type": "result", "url": url, "url_check": url_check, "ssl_check": ssl_check, "domain_check": domain_days, "location_check": country})}\n\n'
            print("-----------------------------------------------------")

        # 모든 URL 검사 완료
        yield f'data: {json.dumps({"type": "done"})}\n\n'

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True)
