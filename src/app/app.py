from flask import Flask, render_template, request, redirect, url_for, flash, g
from markupsafe import Markup
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os, base64, time, requests, threading, re 
from urllib.parse import urlparse
from flask_wtf import FlaskForm
from wtforms import StringField,SubmitField
from wtforms.validators import DataRequired

app = Flask(__name__)

BASE_URL = os.getenv('BASE_URL', 'http://127.0.0.1:5000')
BOT_URL = os.getenv('BOT_URL', 'http://127.0.0.1:8000')
reporting_users = set()
reporting_lock = threading.Lock()

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'sup3r_s3cr3t_k3y')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chall.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_ENABLED'] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    notes = db.relationship('Note', backref = 'author', lazy=True)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class ReportForm(FlaskForm):
    note_url = StringField('Note URL', validators=[DataRequired()])
    submit = SubmitField('Report Note')

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('User already exists')
            return redirect(url_for('register'))
        
        new_user = User(
            username = username,
            password = password
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and password==user.password:
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Invalid credentials')
        return render_template('login.html')
    else:
        return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    notes = Note.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', notes=notes)

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create_note():
    if request.method == 'POST':
        raw = request.form['content']
        safe = raw
        new = Note(content=safe, user_id=current_user.id)
        db.session.add(new)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('create.html')

@app.route('/note', methods=['GET'])
def view_note():
    note_id = request.args.get('Note', type=int) or ''
    note = Note.query.get_or_404(note_id)
    return render_template('view_note.html', note=note, safe_content=Markup(note.content))

@app.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    form = ReportForm()
    log=''
    if form.validate_on_submit():
        print("✅ Received Report:", form.note_url.data)
        note_url = form.note_url.data
        parsed_url = urlparse(note_url)
        base_url_parsed = urlparse(BASE_URL)
        if not parsed_url.scheme.startswith('http'):
            flash('URL must begin with http(s)://', 'error')

        elif parsed_url.netloc == base_url_parsed.netloc and parsed_url.path == '/note' and 'Note=' in parsed_url.query:
            note_id = parsed_url.query.split('=')[-1]
        
            if note_id.isdigit():
                with reporting_lock:
                    if current_user.id in reporting_users:
                        flash('You already have a report in progress.', 'warning')
                    else:
                        reporting_users.add(current_user.id)
                        threading.Thread(target=bot, args=(
                            note_url, current_user.id)).start()
                        flash('Note reported successfully', 'success')
            else:
                flash('Invalid Note ID.', 'error')
        else:
            flash(f'Please provide a valid note URL eg. http://{base_url_parsed.netloc}/note?Note=1', 'error')
        return redirect(url_for('report'))
    return render_template('report.html', form=form)
def bot(note_url, user_id):
    try:
        response = requests.post(f"{BOT_URL}", data={"url": note_url})
        if response.status_code == 200:
            pass
        else:
            pass
    finally:
        with reporting_lock:
            reporting_users.remove(user_id)

def generate_nonce():
    timestamp = int(time.time()) // 1
    return base64.b64encode(str(timestamp).encode()).decode()

@app.before_request
def set_nonce():
    g.nonce = generate_nonce()

@app.context_processor
def inject_nonce():
    return dict(nonce=g.nonce)

@app.after_request
def add_csp(response):
    response.headers["Content-Security-Policy"] = f"default-src 'self' script-src 'nonce-{g.nonce}'"
    return response

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)