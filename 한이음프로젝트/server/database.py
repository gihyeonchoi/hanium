import sqlite3
from datetime import datetime, timedelta, timezone
import json
from contextlib import contextmanager

# 한국 시간대 설정
KST = timezone(timedelta(hours=9))

def get_kst_now():
    """현재 한국 시간 반환"""
    return datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')

class DatabaseManager:
    def __init__(self, db_path='phishing_logs.db'):
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """데이터베이스 연결을 관리하는 컨텍스트 매니저"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_database(self):
        """데이터베이스 초기화 및 테이블 생성"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 로그 테이블 생성
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS phishing_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    client_ip TEXT NOT NULL,
                    original_message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # URL 검사 결과 테이블 생성 (기존)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS url_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    url_check BOOLEAN,
                    ssl_check INTEGER,
                    domain_days INTEGER,
                    country TEXT,
                    risk_level INTEGER,
                    risk_messages TEXT,
                    additional_risks TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (log_id) REFERENCES phishing_logs (id)
                )
            ''')
            
            # 머신러닝 피처 테이블 생성 (새로 추가)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ml_features (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    
                    -- URL 검증 피처
                    url_not_in_db INTEGER DEFAULT 0,  -- 0: DB에 있음, 1: DB에 없음
                    
                    -- SSL 관련 피처
                    ssl_invalid INTEGER DEFAULT 0,     -- 0: 유효, 1: 무효
                    ssl_http_only INTEGER DEFAULT 0,   -- 0: HTTPS, 1: HTTP only
                    ssl_unreachable INTEGER DEFAULT 0, -- 0: 연결 가능, 1: 연결 불가
                    
                    -- 도메인 관련 피처
                    domain_age_days INTEGER DEFAULT -1, -- 도메인 생성일로부터 일수 (-1: 확인불가)
                    
                    -- 국가 피처 (원핫인코딩용)
                    server_country TEXT DEFAULT 'unknown',
                    
                    -- URL 구조 관련 피처
                    has_double_slash INTEGER DEFAULT 0,     -- //가 여러번 포함
                    has_at_symbol INTEGER DEFAULT 0,        -- @ 포함
                    has_ip_address INTEGER DEFAULT 0,       -- IP 주소 직접 사용
                    has_url_shortener INTEGER DEFAULT 0,    -- 단축 URL 서비스
                    has_suspicious_tld INTEGER DEFAULT 0,   -- 의심스러운 TLD (.tk, .ml 등)
                    has_excessive_encoding INTEGER DEFAULT 0, -- 과도한 URL 인코딩
                    
                    -- Open Redirect & XSS 피처
                    has_open_redirect INTEGER DEFAULT 0,    -- Open Redirect 패턴
                    has_xss_pattern INTEGER DEFAULT 0,      -- XSS 패턴
                    
                    -- 동형 문자 공격
                    has_homograph_attack INTEGER DEFAULT 0, -- 키릴/그리스 문자 등
                    homograph_char_count INTEGER DEFAULT 0, -- 발견된 동형 문자 개수
                    
                    -- 리다이렉션 체인
                    redirect_chain_count INTEGER DEFAULT 0, -- URL 체인 개수
                    
                    -- 추가 위험 점수들
                    url_risk_score INTEGER DEFAULT 0,      -- URL 관련 위험 점수
                    ssl_risk_score INTEGER DEFAULT 0,      -- SSL 관련 위험 점수
                    domain_risk_score INTEGER DEFAULT 0,   -- 도메인 관련 위험 점수
                    location_risk_score INTEGER DEFAULT 0, -- 위치 관련 위험 점수
                    additional_risk_score INTEGER DEFAULT 0, -- 추가 위험 점수
                    
                    -- 타겟 변수 (Y)
                    total_risk_score INTEGER DEFAULT 0,    -- 모든 위험 점수의 합
                    
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (log_id) REFERENCES phishing_logs (id)
                )
            ''')
            
            # 제보 테이블 생성 (새로 추가)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS phishing_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_ip TEXT NOT NULL,
                    message_or_url TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',  -- pending, reviewed, processed
                    admin_notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at DATETIME
                )
            ''')
            
            # 인덱스 생성
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON phishing_logs(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_client_ip ON phishing_logs(client_ip)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON url_checks(url)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_risk_level ON url_checks(risk_level)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ml_url ON ml_features(url)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ml_total_risk ON ml_features(total_risk_score)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ml_country ON ml_features(server_country)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_report_status ON phishing_reports(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_report_created ON phishing_reports(created_at)')
    
    def create_log_entry(self, client_ip, original_message=None):
        """새로운 로그 엔트리 생성"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO phishing_logs (client_ip, original_message, timestamp, created_at)
                VALUES (?, ?, ?, ?)
            ''', (client_ip, original_message, get_kst_now(), get_kst_now()))
            return cursor.lastrowid
    
    def add_url_check_result(self, log_id, url, url_check, ssl_check, domain_days, 
                           country, risk_level, risk_messages, additional_risks=None):
        """URL 검사 결과 저장 (기존 함수)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO url_checks 
                (log_id, url, url_check, ssl_check, domain_days, country, 
                 risk_level, risk_messages, additional_risks, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                log_id, url, url_check, ssl_check, domain_days, country,
                risk_level, json.dumps(risk_messages, ensure_ascii=False),
                json.dumps(additional_risks, ensure_ascii=False) if additional_risks else None,
                get_kst_now()
            ))
    
    def add_ml_features(self, log_id, url, features):
        """머신러닝 피처 저장"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # created_at 추가
            features_with_time = features.copy()
            
            # 피처 딕셔너리를 SQL 쿼리로 변환
            columns = ', '.join(features_with_time.keys()) + ', created_at'
            placeholders = ', '.join('?' * len(features_with_time)) + ', ?'
            values = list(features_with_time.values()) + [get_kst_now()]
            
            # log_id와 url 추가
            columns = f'log_id, url, {columns}'
            placeholders = f'?, ?, {placeholders}'
            values = [log_id, url] + values
            
            query = f'''
                INSERT INTO ml_features ({columns})
                VALUES ({placeholders})
            '''
            
            cursor.execute(query, values)
    
    def get_ml_features(self, limit=None):
        """머신러닝용 피처 데이터 조회"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT * FROM ml_features
                ORDER BY created_at DESC
            '''
            
            if limit:
                query += f' LIMIT {limit}'
            
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_ml_features_for_training(self):
        """학습용 피처와 타겟 데이터 반환"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 피처 컬럼들 (타겟 변수와 메타데이터 제외)
            feature_columns = [
                'url_not_in_db', 'ssl_invalid', 'ssl_http_only', 'ssl_unreachable',
                'domain_age_days', 'has_double_slash', 'has_at_symbol',
                'has_ip_address', 'has_url_shortener', 'has_suspicious_tld',
                'has_excessive_encoding', 'has_open_redirect', 'has_xss_pattern',
                'has_homograph_attack', 'homograph_char_count', 'redirect_chain_count'
            ]
            
            columns_str = ', '.join(feature_columns)
            
            query = f'''
                SELECT {columns_str}, server_country, total_risk_score
                FROM ml_features
            '''
            
            cursor.execute(query)
            data = cursor.fetchall()
            
            if not data:
                return None, None, None
            
            # 피처와 타겟 분리
            features = []
            countries = []
            targets = []
            
            for row in data:
                # 숫자 피처들
                feature_values = [row[col] for col in feature_columns]
                features.append(feature_values)
                
                # 국가 (원핫인코딩용)
                countries.append(row['server_country'])
                
                # 타겟 변수
                targets.append(row['total_risk_score'])
            
            return features, countries, targets
    
    def export_ml_features_to_csv(self, filename='ml_features.csv'):
        """머신러닝 피처를 CSV로 내보내기"""
        import csv
        
        features = self.get_ml_features()
        
        if not features:
            print("내보낼 데이터가 없습니다.")
            return
        
        # CSV 파일 작성
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = features[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(features)
        
        print(f"{len(features)}개의 레코드를 {filename}에 저장했습니다.")
    
    def get_logs_by_date_range(self, start_date=None, end_date=None, limit=100):
        """날짜 범위로 로그 조회"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT l.*, COUNT(u.id) as url_count, AVG(u.risk_level) as avg_risk_level
                FROM phishing_logs l
                LEFT JOIN url_checks u ON l.id = u.log_id
                WHERE 1=1
            '''
            params = []
            
            if start_date:
                query += ' AND l.timestamp >= ?'
                params.append(start_date)
            
            if end_date:
                query += ' AND l.timestamp <= ?'
                params.append(end_date)
            
            query += ' GROUP BY l.id ORDER BY l.timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_url_check_details(self, log_id):
        """특정 로그의 URL 검사 상세 결과 조회"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM url_checks WHERE log_id = ?
            ''', (log_id,))
            
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                # JSON 문자열을 파이썬 객체로 변환
                if result['risk_messages']:
                    result['risk_messages'] = json.loads(result['risk_messages'])
                if result['additional_risks']:
                    result['additional_risks'] = json.loads(result['additional_risks'])
                results.append(result)
            
            return results
    
    def get_statistics(self):
        """통계 정보 조회"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 전체 통계
            cursor.execute('''
                SELECT 
                    COUNT(DISTINCT l.id) as total_checks,
                    COUNT(u.id) as total_urls,
                    AVG(u.risk_level) as avg_risk_level,
                    COUNT(CASE WHEN u.risk_level >= 70 THEN 1 END) as high_risk_urls,
                    COUNT(CASE WHEN u.risk_level >= 40 AND u.risk_level < 70 THEN 1 END) as medium_risk_urls,
                    COUNT(CASE WHEN u.risk_level < 40 THEN 1 END) as low_risk_urls
                FROM phishing_logs l
                LEFT JOIN url_checks u ON l.id = u.log_id
            ''')
            overall_stats = dict(cursor.fetchone())
            
            # 국가별 통계
            cursor.execute('''
                SELECT country, COUNT(*) as count, AVG(risk_level) as avg_risk
                FROM url_checks
                GROUP BY country
                ORDER BY count DESC
                LIMIT 10
            ''')
            country_stats = [dict(row) for row in cursor.fetchall()]
            
            # 시간대별 통계 (최근 24시간)
            cursor.execute('''
                SELECT 
                    strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                    COUNT(*) as check_count
                FROM phishing_logs
                WHERE timestamp >= datetime(?, '-24 hours')
                GROUP BY hour
                ORDER BY hour
            ''', (get_kst_now(),))
            hourly_stats = [dict(row) for row in cursor.fetchall()]
            
            # ML 피처 통계 추가
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_ml_records,
                    AVG(total_risk_score) as avg_total_risk,
                    MAX(total_risk_score) as max_total_risk,
                    COUNT(DISTINCT server_country) as unique_countries
                FROM ml_features
            ''')
            ml_stats = dict(cursor.fetchone())
            
            return {
                'overall': overall_stats,
                'by_country': country_stats,
                'hourly': hourly_stats,
                'ml_features': ml_stats
            }
    
    def search_logs(self, search_term=None, risk_level_min=None, country=None):
        """로그 검색"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT DISTINCT l.*, u.url, u.risk_level, u.country
                FROM phishing_logs l
                JOIN url_checks u ON l.id = u.log_id
                WHERE 1=1
            '''
            params = []
            
            if search_term:
                query += ' AND (u.url LIKE ? OR l.original_message LIKE ?)'
                params.extend([f'%{search_term}%', f'%{search_term}%'])
            
            if risk_level_min is not None:
                query += ' AND u.risk_level >= ?'
                params.append(risk_level_min)
            
            if country:
                query += ' AND u.country = ?'
                params.append(country)
            
            query += ' ORDER BY l.timestamp DESC LIMIT 100'
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def cleanup_old_logs(self, days=30):
        """오래된 로그 정리"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = (datetime.now(KST) - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                DELETE FROM phishing_logs 
                WHERE timestamp < ?
            ''', (cutoff_date,))
            
            return cursor.rowcount
    
    def create_report(self, client_ip, message_or_url, reason):
        """피싱 사이트 제보 생성"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO phishing_reports (client_ip, message_or_url, reason, created_at)
                VALUES (?, ?, ?, ?)
            ''', (client_ip, message_or_url, reason, get_kst_now()))
            return cursor.lastrowid
    
    def get_reports(self, status=None, limit=100):
        """제보 목록 조회"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if status:
                cursor.execute('''
                    SELECT * FROM phishing_reports 
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (status, limit))
            else:
                cursor.execute('''
                    SELECT * FROM phishing_reports 
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def update_report_status(self, report_id, status, admin_notes=None):
        """제보 상태 업데이트"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE phishing_reports 
                SET status = ?, admin_notes = ?, reviewed_at = ?
                WHERE id = ?
            ''', (status, admin_notes, get_kst_now(), report_id))
            return cursor.rowcount > 0