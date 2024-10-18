from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from database import Database
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
from PIL import Image
import time
import imghdr
# Импортируем psycopg2 вместо sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Замените на случайную строку
db = Database()

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    try:
        profiles = db.get_random_profiles(10, exclude_id=session['user_id'])
        return render_template('index.html', profiles=profiles)
    except Exception as e:
        print(f"Error in index route: {e}")
        return render_template('index.html', profiles=[], error="Не удалось загрузить профили")

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    try:
        user_id = request.args.get('id', session['user_id'])
        user_profile = db.get_profile(user_id)
        posts = db.get_posts(user_id)
        for post in posts:
            post['comments'] = db.get_comments(post['id'])
        is_own_profile = int(user_id) == session['user_id']
        return render_template('profile.html', profile=user_profile, posts=posts, is_own_profile=is_own_profile)
    except Exception as e:
        print(f"Error in profile route: {e}")
        return "An error occurred", 500

@app.route('/matches')
def matches():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    try:
        matches = db.get_matches(session['user_id'])
        return render_template('matches.html', matches=matches)
    except Exception as e:
        print(f"Error in matches route: {e}")
        return "An error occurred", 500

@app.route('/like', methods=['POST'])
def like():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    liked_profile_id = data['profile_id']
    is_match = db.add_like(session['user_id'], liked_profile_id)
    return jsonify({'match': is_match})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            user = db.get_user_by_email(email)
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                return redirect(url_for('index'))
            return render_template('login.html', error='Неверный email или пароль')
        except Exception as e:
            print(f"Error in login route: {e}")
            return "An error occurred", 500
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        if db.create_user(name, email, hashed_password):
            return redirect(url_for('login'))
        return render_template('register.html', error='Email уже занят')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/load-more')
def load_more():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    offset = int(request.args.get('offset', 0))
    profiles = db.get_random_profiles(10, exclude_id=session['user_id'], offset=offset)
    return jsonify({'profiles': profiles})

@app.route('/edit-profile', methods=['POST'])
def edit_profile():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    name = request.form.get('name')
    age = request.form.get('age')
    bio = request.form.get('bio')
    
    photo_url = None
    if 'photo' in request.files:
        file = request.files['photo']
        if file and file.filename != '':
            filename = secure_filename(f"{session['user_id']}_{int(time.time())}.jpg")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            photo_url = url_for('static', filename=f'uploads/{filename}')

    success = db.update_profile(session['user_id'], name, age, bio, photo_url)
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to update profile'}), 500

@app.route('/create_post', methods=['POST'])
def create_post():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    content = request.form.get('content')
    post_id = db.create_post(session['user_id'], content)
    return jsonify({'success': True, 'post_id': post_id})

@app.route('/add_comment', methods=['POST'])
def add_comment():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    post_id = request.form.get('post_id')
    content = request.form.get('content')
    comment_id = db.add_comment(session['user_id'], post_id, content)
    return jsonify({'success': True, 'comment_id': comment_id})

@app.route('/toggle_like', methods=['POST'])
def toggle_like():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    post_id = request.form.get('post_id')
    if db.add_like(session['user_id'], post_id):
        return jsonify({'success': True, 'action': 'added'})
    else:
        db.remove_like(session['user_id'], post_id)
        return jsonify({'success': True, 'action': 'removed'})

if __name__ == '__main__':
    app.run(debug=True)
