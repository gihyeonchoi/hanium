from flask import Flask, render_template, request, Response, jsonify, send_file, redirect, url_for, session
from pishing_check import URL_parsing, URL_check, SSL_check, Domain_check, Location_to_IP, Additional_risk
from database import DatabaseManager
import json
import time
from datetime import datetime, timedelta
import re
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')
db = DatabaseManager()  # 데이터베이스 매니저 인스턴스 생성

# 관리자 비밀번호 (실제 운영 환경에서는 환경 변수로 설정)
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'vhfflxpr1')

def require_password(f):
    """비밀번호 인증이 필요한 라우트를 위한 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session:
            return redirect(url_for('auth_page', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/auth', methods=['GET', 'POST'])
def auth_page():
    """인증 페이지"""
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['authenticated'] = True
            next_page = request.args.get('next', url_for('admin_dashboard'))
            return redirect(next_page)
        else:
            return render_template('auth.html', error='비밀번호가 틀렸습니다.')
    
    return render_template('auth.html')

@app.route('/logout')
def logout():
    """로그아웃"""
    session.pop('authenticated', None)
    return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/report', methods=['POST'])
def submit_report():
    """피싱 사이트 제보 제출"""
    try:
        data = request.json
        message_or_url = data.get('message_or_url', '').strip()
        reason = data.get('reason', '').strip()
        
        if not message_or_url or not reason:
            return jsonify({'success': False, 'error': '모든 필드를 입력해주세요.'}), 400
        
        client_ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        report_id = db.create_report(client_ip, message_or_url, reason)
        
        return jsonify({'success': True, 'report_id': report_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/analyze')
def analyze():
    query = request.args.get('query', '')
    urls = URL_parsing(query)
    client_ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    
    def generate():
        # 새로운 로그 엔트리 생성
        log_id = db.create_log_entry(client_ip, query)
        
        yield f'data: {json.dumps({"type": "total", "total": len(urls)})}\n\n'
        
        for url in urls:
            yield f'data: {json.dumps({"type": "progress", "message": f"URL 검사 중... ({url})"})}\n\n'
            
            # 머신러닝 피처 초기화
            ml_features = {
                # 기본값 설정
                'url_not_in_db': 0,
                'ssl_invalid': 0,
                'ssl_http_only': 0,
                'ssl_unreachable': 0,
                'domain_age_days': -1,
                'server_country': 'unknown',
                'has_double_slash': 0,
                'has_at_symbol': 0,
                'has_ip_address': 0,
                'has_url_shortener': 0,
                'has_suspicious_tld': 0,
                'has_excessive_encoding': 0,
                'has_open_redirect': 0,
                'has_xss_pattern': 0,
                'has_homograph_attack': 0,
                'homograph_char_count': 0,
                'redirect_chain_count': 0,
                'url_risk_score': 0,
                'ssl_risk_score': 0,
                'domain_risk_score': 0,
                'location_risk_score': 0,
                'additional_risk_score': 0,
                'total_risk_score': 0
            }
            
            # 개별 위험 점수 변수
            url_risk_score = 0
            ssl_risk_score = 0
            domain_risk_score = 0
            location_risk_score = 0
            additional_risk_score = 0
            
            # URL 검사
            url_check = URL_check(url)
            yield f'data: {json.dumps({"type": "progress", "message": "✅ URL 대조 완료"})}\n\n'
            time.sleep(0.1)
            
            # URL 검사 피처 설정
            if not url_check:
                ml_features['url_not_in_db'] = 1
                url_risk_score += 20

            # SSL 검사
            ssl_check = SSL_check(url)
            yield f'data: {json.dumps({"type": "progress", "message": "✅ SSL 인증서 검사 완료"})}\n\n'
            time.sleep(0.1)
            
            # SSL 검사 피처 설정
            if ssl_check == 0:
                ml_features['ssl_invalid'] = 1
                ssl_risk_score += 25
            elif ssl_check == -1:
                ml_features['ssl_http_only'] = 1
                ssl_risk_score += 15
            elif ssl_check == -2:
                ml_features['ssl_unreachable'] = 1
                ssl_risk_score += 20

            # 도메인 생성일 검사
            domain_days = Domain_check(url)
            yield f'data: {json.dumps({"type": "progress", "message": "✅ 도메인 생성일 확인 완료"})}\n\n'
            time.sleep(0.1)
            
            # 도메인 피처 설정
            ml_features['domain_age_days'] = domain_days
            if 0 < domain_days < 180:
                domain_risk_score += 30
            elif domain_days <= 0:
                domain_risk_score += 15

            # IP 위치 확인
            location_ok, country = Location_to_IP(url)
            yield f'data: {json.dumps({"type": "progress", "message": "✅ IP 위치 확인 완료"})}\n\n'
            time.sleep(0.1)
            
            # 국가 피처 설정
            ml_features['server_country'] = country
            if country not in ["대한민국", "한국", "알수없음"]:
                location_risk_score += 15
            elif country == "알수없음":
                location_risk_score += 20

            # 추가 위험 요소 검사
            additional_risk_score_raw, additional_risk_msg = Additional_risk(url)
            yield f'data: {json.dumps({"type": "progress", "message": "✅ 추가 서버 정보 탐지 완료"})}\n\n'
            time.sleep(0.1)
            
            # Additional_risk에서 반환된 피처들을 파싱
            if additional_risk_msg:
                for msg in additional_risk_msg:
                    if '//' in msg and '리다이렉션 경로' in msg:
                        ml_features['has_double_slash'] = 1
                    elif '@' in msg and '인증 우회' in msg:
                        ml_features['has_at_symbol'] = 1
                    elif 'Open Redirect' in msg:
                        ml_features['has_open_redirect'] = 1
                    elif 'XSS' in msg:
                        ml_features['has_xss_pattern'] = 1
                    elif '영어로 위장한 문자' in msg:
                        ml_features['has_homograph_attack'] = 1
                        # 동형 문자 개수 추출
                        import re
                        match = re.search(r'(\d+)개의', msg)
                        if match:
                            ml_features['homograph_char_count'] = int(match.group(1))
                    elif 'IP 주소가 직접 사용' in msg:
                        ml_features['has_ip_address'] = 1
                    elif '단축 URL' in msg:
                        ml_features['has_url_shortener'] = 1
                    elif '무료 도메인' in msg:
                        ml_features['has_suspicious_tld'] = 1
                    elif '과도한 URL 인코딩' in msg:
                        ml_features['has_excessive_encoding'] = 1
                    elif '다중 리다이렉션' in msg:
                        # 리다이렉션 체인 개수 추출
                        match = re.search(r'(\d+)개의 URL', msg)
                        if match:
                            ml_features['redirect_chain_count'] = int(match.group(1))
            
            additional_risk_score = additional_risk_score_raw

            # 위험도 평가 (화면 표시용)
            risk_score = 0
            risk_messages = []
            
            # 추가 서버 정보 평가
            if additional_risk_msg:
                risk_score += additional_risk_score
                risk_messages.extend(additional_risk_msg)
                
            # URL 대조 결과 평가
            if not url_check:
                risk_score += 30
                risk_messages.append("데이터베이스에 등록되지 않은 도메인입니다.")
            
            # SSL 인증서 평가
            if ssl_check == 0:
                risk_score += 25
                risk_messages.append("SSL 인증서가 유효하지 않습니다.")
            elif ssl_check == -1:
                risk_score += 15
                risk_messages.append("HTTP 연결입니다. SSL 인증서가 존재하지 않습니다.")
            
            # 도메인 생성일 평가
            if 0 < domain_days < 180:
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

            # 위험도 레벨 계산 (화면 표시용, 0-100으로 제한)
            risk_level_display = min(100, risk_score)
            
            # 머신러닝용 개별 위험 점수 저장
            ml_features['url_risk_score'] = url_risk_score
            ml_features['ssl_risk_score'] = ssl_risk_score
            ml_features['domain_risk_score'] = domain_risk_score
            ml_features['location_risk_score'] = location_risk_score
            ml_features['additional_risk_score'] = additional_risk_score
            
            # 총 위험 점수 (제한 없이 모든 점수의 합)
            ml_features['total_risk_score'] = (
                url_risk_score + 
                ssl_risk_score + 
                domain_risk_score + 
                location_risk_score + 
                additional_risk_score
            )
            
            # 데이터베이스에 결과 저장
            db.add_url_check_result(
                log_id=log_id,
                url=url,
                url_check=url_check,
                ssl_check=ssl_check,
                domain_days=domain_days,
                country=country,
                risk_level=risk_level_display,  # 화면 표시용 (0-100)
                risk_messages=risk_messages,
                additional_risks=additional_risk_msg if additional_risk_msg else None
            )
            
            # 머신러닝 피처 저장
            db.add_ml_features(log_id, url, ml_features)

            # 최종 결과 전송
            yield f'data: {json.dumps({"type": "result", "url": url, "url_check": url_check, "ssl_check": ssl_check, "domain_check": domain_days, "location_check": country, "risk_level": risk_level_display, "risk_messages": risk_messages})}\n\n'
            print("-----------------------------------------------------")

        # 모든 URL 검사 완료
        yield f'data: {json.dumps({"type": "done"})}\n\n'

    return Response(generate(), mimetype='text/event-stream')

# API 엔드포인트
@app.route('/api/logs')
@require_password
def get_logs():
    """로그 조회 API"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    limit = request.args.get('limit', 100, type=int)
    
    logs = db.get_logs_by_date_range(start_date, end_date, limit)
    return jsonify(logs)

@app.route('/api/logs/<int:log_id>')
@require_password
def get_log_details(log_id):
    """특정 로그의 상세 정보 조회 API"""
    details = db.get_url_check_details(log_id)
    return jsonify(details)

@app.route('/api/statistics')
@require_password
def get_statistics():
    """통계 정보 조회 API"""
    stats = db.get_statistics()
    return jsonify(stats)

@app.route('/api/search')
@require_password
def search_logs():
    """로그 검색 API"""
    search_term = request.args.get('q')
    risk_level_min = request.args.get('risk_level', type=int)
    country = request.args.get('country')
    
    results = db.search_logs(search_term, risk_level_min, country)
    return jsonify(results)

@app.route('/api/cleanup', methods=['POST'])
@require_password
def cleanup_logs():
    """오래된 로그 정리 API"""
    days = request.json.get('days', 30)
    deleted_count = db.cleanup_old_logs(days)
    return jsonify({'deleted': deleted_count})

# 머신러닝 관련 API 엔드포인트
@app.route('/api/ml/features')
@require_password
def get_ml_features():
    """머신러닝 피처 조회 API"""
    limit = request.args.get('limit', type=int)
    features = db.get_ml_features(limit)
    return jsonify(features)

@app.route('/api/ml/export')
@require_password
def export_ml_features():
    """머신러닝 피처 CSV 내보내기"""
    try:
        filename = f'ml_features_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        db.export_ml_features_to_csv(filename)
        return send_file(filename, as_attachment=True, mimetype='text/csv')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ml/training-data')
@require_password
def get_training_data():
    """학습용 데이터 조회 API"""
    features, countries, targets = db.get_ml_features_for_training()
    
    if features is None:
        return jsonify({'error': '학습 데이터가 없습니다.'}), 404
    
    return jsonify({
        'features': features,
        'countries': countries,
        'targets': targets,
        'feature_names': [
            'url_not_in_db', 'ssl_invalid', 'ssl_http_only', 'ssl_unreachable',
            'domain_age_days', 'has_double_slash', 'has_at_symbol',
            'has_ip_address', 'has_url_shortener', 'has_suspicious_tld',
            'has_excessive_encoding', 'has_open_redirect', 'has_xss_pattern',
            'has_homograph_attack', 'homograph_char_count', 'redirect_chain_count'
        ]
    })

# 관리자 대시보드
@app.route('/admin')
@require_password
def admin_dashboard():
    """관리자 대시보드 페이지"""
    return render_template('admin.html')

# 머신러닝 대시보드
@app.route('/ml-dashboard')
@require_password
def ml_dashboard():
    """머신러닝 피처 대시보드"""
    return render_template('ml_dashboard.html')

# 제보 관리 API
@app.route('/api/reports')
@require_password
def get_reports():
    """제보 목록 조회"""
    status = request.args.get('status')
    reports = db.get_reports(status)
    return jsonify(reports)

@app.route('/api/reports/<int:report_id>', methods=['PUT'])
@require_password
def update_report(report_id):
    """제보 상태 업데이트"""
    data = request.json
    status = data.get('status')
    admin_notes = data.get('admin_notes')
    
    if status not in ['pending', 'reviewed', 'processed']:
        return jsonify({'error': '유효하지 않은 상태입니다.'}), 400
    
    success = db.update_report_status(report_id, status, admin_notes)
    return jsonify({'success': success})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)