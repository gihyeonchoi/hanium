from flask import Flask, render_template, request, jsonify
from pishing_check import URL_parsing, URL_check, SSL_check, Domain_check, Location_to_IP

app = Flask(__name__)

@app.route('/')
def search_form():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')
    urls = URL_parsing(query)
    results = []
    print(urls)
    for url in urls:
        result = {'url': url, 'progress': []}

        # URL Check
        url_check_result = URL_check(url)
        result['progress'].append({'step': 'URL Check', 'result': url_check_result})

        # SSL Check
        ssl_check_result = SSL_check(url)
        result['progress'].append({'step': 'SSL Check', 'result': ssl_check_result})

        # Domain Check
        domain_age = Domain_check(url)
        result['progress'].append({'step': 'Domain Check', 'result': domain_age})

        # Location to IP
        location_result = Location_to_IP(url)
        result['progress'].append({'step': 'Location Check', 'result': location_result})

        results.append(result)

    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)
