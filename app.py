from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/authenticate')
def authenticate():
    return render_template('authenticate.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/create_entry')
def create_entry():
    return render_template('create_entry.html')

if __name__ == '__main__':
    app.run(debug=True)
