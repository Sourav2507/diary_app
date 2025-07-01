import os
import json
from flask import Flask, render_template, redirect, request, session, url_for, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore
from functools import wraps

# 🔐 Firebase setup
firebase_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
cred_dict = json.loads(firebase_json)
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)
db = firestore.client()

# 🔧 Flask setup
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default_secret_key")
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# 🔐 Auth wrapper
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('authenticate'))
        return f(*args, **kwargs)
    return wrapper

# 🎨 Theme background image map
def get_theme_image(theme_name):
    return {
        'sunset': '/static/images/sunset.jpg',
        'ocean': '/static/images/ocean.jpg',
        'mountains': '/static/images/mountains.jpg',
        'night': '/static/images/night.jpg',
        'parchment': '/static/images/parchment.jpg',
        'light': '/static/images/light.jpg'
    }.get(theme_name, '/static/images/default.jpg')


# 🔽 Routes

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

@app.route('/create_diary', methods=['POST'])
@login_required
def create_diary():
    data = request.get_json()
    title = data.get('title')
    theme = data.get('theme')
    user_id = session['user']['uid']

    diary_ref = db.collection('users').document(user_id).collection('diaries').document()
    diary_ref.set({
        'title': title,
        'theme': theme,
        'created_at': firestore.SERVER_TIMESTAMP,
        'last_edited': firestore.SERVER_TIMESTAMP
    })

    return jsonify({'success': True, 'diary_id': diary_ref.id})

@app.route('/api/diaries')
@login_required
def get_diaries():
    user_id = session['user']['uid']
    diaries_ref = db.collection('users').document(user_id).collection('diaries')
    diaries = diaries_ref.order_by('last_edited', direction=firestore.Query.DESCENDING).stream()

    diary_list = [{
        'id': diary.id,
        'title': diary.to_dict().get('title'),
        'theme': diary.to_dict().get('theme'),
        'last_edited': diary.to_dict().get('last_edited').isoformat() if diary.to_dict().get('last_edited') else ''
    } for diary in diaries]

    return jsonify(diary_list)

@app.route('/delete_diary/<diary_id>', methods=['DELETE'])
@login_required
def delete_diary(diary_id):
    try:
        user_id = session['user']['uid']
        diary_ref = db.collection('users').document(user_id).collection('diaries').document(diary_id)
        if diary_ref.get().exists:
            diary_ref.delete()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Diary not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/diary/<diary_id>')
@login_required
def diary_page(diary_id):
    user_id = session['user']['uid']
    diary_ref = db.collection('users').document(user_id).collection('diaries').document(diary_id)
    diary_doc = diary_ref.get()

    if not diary_doc.exists:
        return "Diary not found", 404

    diary_data = diary_doc.to_dict()
    title = diary_data.get('title', 'Untitled Diary')
    theme = diary_data.get('theme', 'default_theme')

    entries_ref = diary_ref.collection('entries').order_by('created_at', direction=firestore.Query.DESCENDING)
    entries_docs = entries_ref.stream()

    entries = []
    for doc in entries_docs:
        data = doc.to_dict()
        created_at = data.get('created_at')
        if hasattr(created_at, 'strftime'):
            formatted_date = created_at.strftime('%B %d, %Y')
        else:
            formatted_date = 'Unknown Date'
        entries.append({
            'date': formatted_date,
            'content': data.get('content', '')
        })

    background_url = get_theme_image(theme)

    return render_template(
        'diary_page.html',
        diary_id=diary_id,
        diary_title=title,
        background_image_url=background_url,
        entries=entries
    )

@app.route('/add_entry/<diary_id>', methods=['POST'])
@login_required
def add_entry(diary_id):
    user_id = session['user']['uid']
    content = request.form.get('content')

    if not content:
        return redirect(url_for('diary_page', diary_id=diary_id))

    entry_ref = db.collection('users').document(user_id).collection('diaries').document(diary_id).collection('entries').document()
    entry_ref.set({
        'content': content,
        'created_at': firestore.SERVER_TIMESTAMP
    })

    db.collection('users').document(user_id).collection('diaries').document(diary_id).update({
        'last_edited': firestore.SERVER_TIMESTAMP
    })

    return redirect(url_for('diary_page', diary_id=diary_id))

@app.route('/verify_token', methods=['POST'])
def verify_token():
    id_token = request.json.get("idToken")
    try:
        decoded_token = auth.verify_id_token(id_token)
        session['user'] = decoded_token
        return {'success': True}, 200
    except Exception as e:
        return {'success': False, 'error': str(e)}, 401

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# 🔥 Run the app
if __name__ == '__main__':
    app.run(debug=True)
