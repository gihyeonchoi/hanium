from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def search_form():
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('query', '')
    return render_template('search.html', query=query)

if __name__ == '__main__':
    app.run(debug=True)
