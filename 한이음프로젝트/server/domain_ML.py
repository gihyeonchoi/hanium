

kor_net_original = pd.read_csv('all_subdomains_response.csv')
kor_net = kor_net_original[kor_net_original['Response Code'].notna()]
kor_net = kor_net[['W_Protocol']]

fishing_net_original = pd.read_csv('verified_online.csv')

한국인터넷진흥원 = pd.read_csv('한국인터넷진흥원_피싱사이트.csv')


def clean_url(url):
    # https:// 뒤의 첫 번째 / 이후 텍스트를 제거하는 정규식
    cleaned_url = re.sub(r'^(https://[^/]+).*', r'\1', url)
    return cleaned_url

# url 컬럼에 clean_url 함수 적용하여 새로운 'cleaned_url' 컬럼 생성
fishing_net_original['cleaned_url'] = fishing_net_original['url'].apply(clean_url)

# 'cleaned_url'만 포함된 새로운 DataFrame 생성
fishing_net = fishing_net_original[['cleaned_url']]























import pandas as pd
import re

# 정상 URL
kor_net_original = pd.read_csv('all_subdomains_response.csv')
kor_net = kor_net_original[kor_net_original['Response Code'].notna()]
df_good = kor_net[['W_Protocol']]
df_good = df_good[['W_Protocol']].rename(columns={'W_Protocol': 'url'})
df_good['label'] = 0

# 피싱 URL
한국인터넷진흥원 = pd.read_csv('한국인터넷진흥원_피싱사이트.csv')
df_bad = 한국인터넷진흥원.sample(n=5000, random_state=42)
df_bad = df_bad[['홈페이지주소']].rename(columns={'홈페이지주소': 'url'})
df_bad['label'] = 1

# 합치기
df = pd.concat([df_good, df_bad], ignore_index=True).drop_duplicates()
df = df[df['url'].notnull()].reset_index(drop=True)




from urllib.parse import urlparse

# 도메인만 추출
def extract_domain(url):
    try:
        parsed = urlparse(url if '://' in url else 'http://' + url)
        return parsed.netloc.lower()
    except:
        return ''

df['domain'] = df['url'].apply(extract_domain)

# 특수문자 수 (예: - . _ 등)
def count_special_chars(domain):
    return len(re.findall(r'[^a-zA-Z0-9]', domain))

df['num_special'] = df['domain'].apply(count_special_chars)

# 도메인 길이
df['domain_len'] = df['domain'].apply(lambda x: len(x))

# 서브도메인 수 (예: a.b.c.com → 3개)
df['num_subdomains'] = df['domain'].apply(lambda d: d.count('.'))

# 주요 단축 URL 여부 (피싱에서 자주 등장하는 도메인들)
shorteners = ['bit.ly', 'han.gl', 't.ly', 'url.kr', 'me2.do', 'is.gd', 'c11.kr']

df['is_shortener'] = df['domain'].apply(lambda d: 1 if d in shorteners else 0)



X = df[['num_special', 'domain_len', 'num_subdomains', 'is_shortener']]
y = df['label']

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

X_train, X_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=42)

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))


def predict_url_list(url_list):
    # 입력 URL DataFrame 생성
    input_df = pd.DataFrame({'url': url_list})
    input_df['domain'] = input_df['url'].apply(extract_domain)
    input_df['num_special'] = input_df['domain'].apply(count_special_chars)
    input_df['domain_len'] = input_df['domain'].apply(lambda x: len(x))
    input_df['num_subdomains'] = input_df['domain'].apply(lambda d: d.count('.'))
    input_df['is_shortener'] = input_df['domain'].apply(lambda d: 1 if d in shorteners else 0)

    # 예측에 사용할 피처
    X_input = input_df[['num_special', 'domain_len', 'num_subdomains', 'is_shortener']]
    
    # 예측
    predictions = model.predict(X_input)
    probs = model.predict_proba(X_input)

    # 결과 출력
    for url, pred, prob in zip(url_list, predictions, probs):
        print(f"[{url}] → {'피싱 사이트' if pred == 1 else '정상'} (피싱 확률: {prob[1]:.2%})")

predict_url_list(["https://cafe.naver.com"])




































from urllib.parse import urlparse

def extract_features(url):
    try:
        parsed = urlparse(url if url.startswith("http") else "http://" + url)
        domain = parsed.netloc
        path = parsed.path

        features = {
            'domain': domain,
            'path_len': len(path),
            'num_digits': len(re.findall(r'\d', path)),
            'num_letters': len(re.findall(r'[a-zA-Z]', path)),
            'num_special': len(re.findall(r'[^a-zA-Z0-9]', path)),
            'has_https': int(parsed.scheme == 'https'),
            'is_short_url': int(domain in {'t.ly', 'bit.ly', 'han.gl', 'c11.kr'}),
            'endswith_com': int(domain.endswith('.com')),
            'endswith_kr': int(domain.endswith('.kr'))
        }
        return pd.Series(features)
    except:
        return pd.Series({
            'domain': '', 'path_len': 0, 'num_digits': 0, 'num_letters': 0,
            'num_special': 0, 'has_https': 0, 'is_short_url': 0,
            'endswith_com': 0, 'endswith_kr': 0
        })

features_df = df['url'].apply(extract_features)
df = pd.concat([df, features_df], axis=1)


from sklearn.feature_extraction.text import TfidfVectorizer

tfidf = TfidfVectorizer(max_features=300)
domain_tfidf = tfidf.fit_transform(df['domain'])



from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# 도메인 벡터를 DataFrame으로 만들 때, 컬럼명을 str로 변환
tfidf_df = pd.DataFrame(domain_tfidf.toarray())
tfidf_df.columns = tfidf_df.columns.astype(str)  # <- 이거 추가!

# 숫자 특징도 DataFrame으로 변환 (이미 문자열 컬럼일 가능성 높지만 확실히)
X_numeric = df[['path_len', 'num_digits', 'num_letters', 'num_special',
                'has_https', 'is_short_url', 'endswith_com', 'endswith_kr']]
X_numeric.columns = X_numeric.columns.astype(str)  # <- 이거도 추가!

# 최종 X
X = pd.concat([X_numeric.reset_index(drop=True), tfidf_df.reset_index(drop=True)], axis=1)

y = df['label']

X_train, X_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=42)

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)


def predict_url(url):
    feat = extract_features(url)
    domain_vec = tfidf.transform([feat['domain']])
    x_numeric = feat.drop('domain').values.reshape(1, -1)
    x_combined = pd.concat([pd.DataFrame(x_numeric), pd.DataFrame(domain_vec.toarray())], axis=1)
    prob = model.predict_proba(x_combined)[0][1]
    return round(prob * 100, 2)  # 예: 87.24 (% 확률)

print(predict_url("https://google.com"))
