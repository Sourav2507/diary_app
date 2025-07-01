import os
import json
from flask import Flask, render_template, redirect, request, session, url_for
import firebase_admin
from firebase_admin import credentials, auth
from functools import wraps

# 🔐 Load Firebase credentials from environment
firebase_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
cred_dict = json.loads(firebase_json)
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)

# 🔧 Flask app setup
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default_secret_key")

# ✅ Recommended session configs for HTTPS deployment (e.g., Render)
app.config['SESSION_COOKIE_SECURE'] = True  # for HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # safe default for most use cases

# 🔐 Login required decorator
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('authenticate'))
        return f(*args, **kwargs)
    return wrapper

# 🌐 Routes

@app.route('/')
def landing():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/authenticate')
def authenticate():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('authenticate.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/create_entry')
@login_required
def create_entry():
    return render_template('create_entry.html')

@app.route('/verify_token', methods=['POST'])
def verify_token():
    id_token = request.json.get("idToken")
    try:
        decoded_token = auth.verify_id_token(id_token)
        print("✅ Firebase token verified:", decoded_token['uid'])  # Debug log
        session['user'] = decoded_token  # Store the user's token/session info
        return {'success': True}, 200
    except Exception as e:
        print("❌ Token verification failed:", e)
        return {'success': False, 'error': str(e)}, 401

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('authenticate'))

# 🔥 Run the app
if __name__ == '__main__':
    app.run(debug=True)
