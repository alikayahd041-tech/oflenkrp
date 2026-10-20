import os
import json
from datetime import datetime
from functools import wraps
from flask import Flask, render_template_string, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'of-lenk-rp-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///oflenkrp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ============================================================
# ROLLER VE YETKİ SİSTEMİ
# ============================================================
ROLES = {
    'Project Manager': 100,
    'Deputy Project Manager': 90,
    'Project Koordinatör': 80,
    'Chief Administrator': 70,
    'Deputy Chief Administrator': 60,
    'Senior Administrator': 50,
    'Junior Administrator': 40,
    'The Server Administrator': 30,
    'Admin Asistan': 20,
    'Player': 10,
}

def role_level(name):
    return ROLES.get(name, 0)

def requires_role(min_role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if role_level(current_user.role) < role_level(min_role):
                flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ============================================================
# VERİTABANI MODELLERİ
# ============================================================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    static_id = db.Column(db.String(50))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(80), default='Player')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pw): self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)
    @property
    def role_level(self): return role_level(self.role)
    @property
    def is_admin(self): return self.role_level >= role_level('Junior Administrator')

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50))
    subcategory = db.Column(db.String(80))
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User', backref='posts')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))
    data = db.Column(db.Text)
    applicant_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    applicant = db.relationship('User', backref='applications')
    status = db.Column(db.String(20), default='Beklemede')
    admin_note = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))
    data = db.Column(db.Text)
    complainant_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    complainant = db.relationship('User', backref='complaints')
    status = db.Column(db.String(20), default='Beklemede')
    admin_note = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))

# ============================================================
# HTML ŞABLONU (BASE)
# ============================================================
BASE_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>{% block title %}Of LENK RP{% endblock %}</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Segoe UI',Tahoma,sans-serif;background:#f4f6fb;color:#2c3e50;min-height:100vh;}
nav{background:linear-gradient(90deg,#1e3c72,#2a5298);padding:15px 30px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 2px 10px rgba(0,0,0,0.15);flex-wrap:wrap;gap:10px;}
nav .logo{color:#fff;font-size:22px;font-weight:bold;}
nav ul{list-style:none;display:flex;gap:18px;flex-wrap:wrap;}
nav ul li a{color:#fff;text-decoration:none;font-weight:500;transition:0.2s;font-size:14px;}
nav ul li a:hover{color:#f1c40f;}
.user-info{color:#fff;display:flex;align-items:center;gap:10px;font-size:14px;flex-wrap:wrap;}
.badge{background:#f1c40f;color:#1e3c72;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:bold;}
.container{max-width:1200px;margin:30px auto;padding:0 20px;}
.card{background:#fff;border-radius:12px;padding:25px;box-shadow:0 4px 15px rgba(0,0,0,0.08);margin-bottom:20px;}
.card h2{color:#1e3c72;margin-bottom:15px;}
.btn{display:inline-block;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:bold;border:none;cursor:pointer;transition:0.2s;font-size:14px;}
.btn-primary{background:#2a5298;color:#fff;}
.btn-primary:hover{background:#1e3c72;}
.btn-success{background:#27ae60;color:#fff;}
.btn-danger{background:#e74c3c;color:#fff;}
.btn-warning{background:#f39c12;color:#fff;}
.btn-sm{padding:6px 12px;font-size:12px;}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px;}
.card-link{background:#fff;padding:25px;border-radius:12px;text-decoration:none;color:#2c3e50;box-shadow:0 4px 15px rgba(0,0,0,0.08);transition:0.2s;display:block;border-left:5px solid #2a5298;}
.card-link:hover{transform:translateY(-3px);box-shadow:0 8px 20px rgba(0,0,0,0.15);}
.card-link h3{color:#1e3c72;margin-bottom:10px;}
.card-link p{color:#7f8c8d;font-size:14px;}
.flash{padding:12px 20px;border-radius:8px;margin-bottom:15px;font-weight:500;}
.flash.success{background:#d4edda;color:#155724;}
.flash.danger{background:#f8d7da;color:#721c24;}
.flash.info{background:#d1ecf1;color:#0c5460;}
.flash.warning{background:#fff3cd;color:#856404;}
input,textarea,select{width:100%;padding:10px 14px;border:1px solid #dcdde1;border-radius:8px;font-size:14px;margin-bottom:15px;font-family:inherit;}
label{display:block;font-weight:600;margin-bottom:5px;color:#34495e;}
table{width:100%;border-collapse:collapse;}
th,td{padding:12px;text-align:left;border-bottom:1px solid #eee;}
th{background:#f8f9fa;color:#1e3c72;}
.status-Beklemede{color:#f39c12;font-weight:bold;}
.status-Kabul{color:#27ae60;font-weight:bold;}
.status-Red{color:#e74c3c;font-weight:bold;}
.post-item{padding:15px;background:#f8f9fa;border-radius:8px;margin-bottom:12px;border-left:4px solid #2a5298;}
.post-item h4{color:#1e3c72;margin-bottom:8px;}
.post-meta{font-size:12px;color:#7f8c8d;margin-top:8px;}
.hero{background:linear-gradient(135deg,#1e3c72,#2a5298);color:#fff;padding:60px 30px;border-radius:15px;text-align:center;margin-bottom:30px;}
.hero h1{font-size:36px;margin-bottom:15px;}
.hero p{font-size:18px;opacity:0.9;}
h3.section{color:#1e3c72;margin:20px 0 10px;border-bottom:2px solid #eaeaea;padding-bottom:5px;}
</style>
</head>
<body>
<nav>
<div class="logo">🎮 Of LENK RP</div>
<ul>
<li><a href="{{ url_for('index') }}">Ana Sayfa</a></li>
<li><a href="{{ url_for('rules') }}">Kurallar</a></li>
<li><a href="{{ url_for('companies') }}">Şirketler</a></li>
<li><a href="{{ url_for('government') }}">Devlet</a></li>
<li><a href="{{ url_for('ghetto') }}">Getto</a></li>
<li><a href="{{ url_for('applications') }}">Başvurular</a></li>
<li><a href="{{ url_for('complaints') }}">Şikayetler</a></li>
{% if current_user.is_authenticated and current_user.is_admin %}
<li><a href="{{ url_for('admin_panel') }}">Admin</a></li>
{% endif %}
{% if current_user.is_authenticated and current_user.role_level >= 80 %}
<li><a href="{{ url_for('roles_manage') }}">Rol Yönet</a></li>
{% endif %}
</ul>
<div class="user-info">
{% if current_user.is_authenticated %}
<span>👤 {{ current_user.username }}</span>
<span class="badge">{{ current_user.role }}</span>
<a href="{{ url_for('logout') }}" class="btn btn-danger btn-sm">Çıkış</a>
{% else %}
<a href="{{ url_for('login') }}" class="btn btn-primary btn-sm">Giriş</a>
<a href="{{ url_for('register') }}" class="btn btn-success btn-sm">Kayıt</a>
{% endif %}
</div>
</nav>
<div class="container">
{% with messages = get_flashed_messages(with_categories=true) %}
{% for cat, msg in messages %}<div class="flash {{ cat }}">{{ msg }}</div>{% endfor %}
{% endwith %}
{% block content %}{% endblock %}
</div>
</body>
</html>
"""

# ============================================================
# ROUTE'LAR (SAYFALAR)
# ============================================================
@app.route('/')
def index():
    latest = Post.query.order_by(Post.created_at.desc()).limit(5).all()
    return render_template_string(BASE_HTML + """
{% block content %}
<div class="hero">
<h1>🎮 Of LENK RP Forum</h1>
<p>Sunucu Kuralları • Başvurular • Şikayetler • Devlet • Getto</p>
</div>
<div class="grid">
<a href="{{ url_for('rules') }}" class="card-link"><h3>📜 Kurallar</h3><p>Genel, Devlet, Liderlik ve Yeşil Bölge kuralları</p></a>
<a href="{{ url_for('companies') }}" class="card-link"><h3>🏢 Şirketler</h3><p>Şirket içerikleri</p></a>
<a href="{{ url_for('government') }}" class="card-link"><h3>🏛️ Devlet Kurumları</h3><p>Hastane, Ordu, Polis, FBI, Medya, Belediye</p></a>
<a href="{{ url_for('ghetto') }}" class="card-link"><h3>⚔️ Getto</h3><p>Fangs, Wolves, Rawens</p></a>
<a href="{{ url_for('applications') }}" class="card-link"><h3>📝 Başvurular</h3><p>Liderlik, Yönetici, Asistan</p></a>
<a href="{{ url_for('complaints') }}" class="card-link"><h3>⚠️ Şikayetler</h3><p>Oyuncu ve Yönetici şikayetleri</p></a>
</div>
<div class="card" style="margin-top:30px;">
<h2>📢 Son Paylaşımlar</h2>
{% if latest_posts %}
{% for p in latest_posts %}
<div class="post-item">
<h4>{{ p.title }}</h4>
<p>{{ p.content[:200] }}{% if p.content|length > 200 %}...{% endif %}</p>
<div class="post-meta">👤 {{ p.author.username }} • {{ p.created_at.strftime('%d.%m.%Y %H:%M') }}</div>
</div>
{% endfor %}
{% else %}<p>Henüz paylaşım yok.</p>{% endif %}
</div>
{% endblock %}
""", latest_posts=latest)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(username=request.form.get('username')).first()
        if u and u.check_password(request.form.get('password')):
            login_user(u)
            return redirect(url_for('index'))
        flash('Hatalı giriş.', 'danger')
    return render_template_string(BASE_HTML + """
{% block content %}
<div class="card" style="max-width:450px;margin:50px auto;">
<h2>🔐 Giriş Yap</h2>
<form method="POST">
<label>Kullanıcı Adı</label><input type="text" name="username" required>
<label>Şifre</label><input type="password" name="password" required>
<button class="btn btn-primary" type="submit" style="width:100%;">Giriş Yap</button>
</form>
</div>
{% endblock %}
""")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if not User.query.filter_by(username=request.form.get('username')).first():
            u = User(username=request.form.get('username'), static_id=request.form.get('static_id'))
            u.set_password(request.form.get('password'))
            db.session.add(u); db.session.commit()
            return redirect(url_for('login'))
        flash('Kullanıcı adı alınmış.', 'danger')
    return render_template_string(BASE_HTML + """
{% block content %}
<div class="card" style="max-width:450px;margin:50px auto;">
<h2>📝 Kayıt Ol</h2>
<form method="POST">
<label>Kullanıcı Adı</label><input type="text" name="username" required>
<label>Statik ID</label><input type="text" name="static_id">
<label>Şifre</label><input type="password" name="password" required>
<button class="btn btn-success" type="submit" style="width:100%;">Kayıt Ol</button>
</form>
</div>
{% endblock %}
""")

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

# ----- KURALLAR -----
@app.route('/rules')
def rules():
    posts = Post.query.filter_by(category='rules').order_by(Post.created_at.desc()).all()
    return render_template_string(BASE_HTML + """
{% block content %}
<div class="card">
<h2>📜 Kurallar</h2>
{% if current_user.is_authenticated and current_user.is_admin %}
<a href="{{ url_for('new_post', cat='rules') }}" class="btn btn-primary" style="margin-bottom:15px;">+ Yeni Kural</a>
{% endif %}
{% for p in posts %}
<div class="post-item">
<h4>[{{ p.subcategory }}] {{ p.title }}</h4>
<p>{{ p.content }}</p>
<div class="post-meta">👤 {{ p.author.username }} • {{ p.created_at.strftime('%d.%m.%Y') }}</div>
</div>
{% else %}<p>Kural yok.</p>{% endfor %}
</div>
{% endblock %}
""", posts=posts)

# ----- GENEL POST EKLEME -----
@app.route('/post/new/<cat>', methods=['GET', 'POST'])
@requires_role('Junior Administrator')
def new_post(cat):
    if request.method == 'POST':
        p = Post(category=cat, subcategory=request.form.get('subcategory'),
                 title=request.form.get('title'), content=request.form.get('content'),
                 author_id=current_user.id)
        db.session.add(p); db.session.commit()
        return redirect(url_for(cat))
    
    cats = {
        'rules': ['Genel Kurallar', 'Devlet Kuralları', 'Liderlik Kuralları', 'Yeşil Bölge'],
        'companies': ['Şirketler', 'İçerikler'],
        'government': ['Hastane', 'Ordu', 'Polis', 'FBI', 'Medya', 'Belediye'],
        'ghetto': ['Fangs', 'Wolves', 'Rawens']
    }
    return render_template_string(BASE_HTML + """
{% block content %}
<div class="card" style="max-width:700px;margin:0 auto;">
<h2>Yeni İçerik Ekle ({{ cat }})</h2>
<form method="POST">
<label>Kategori</label>
<select name="subcategory">{% for c in cats %}<option>{{ c }}</option>{% endfor %}</select>
<label>Başlık</label><input type="text" name="title" required>
<label>İçerik</label><textarea name="content" rows="8" required></textarea>
<button class="btn btn-primary" type="submit">Kaydet</button>
<a href="{{ url_for(cat) }}" class="btn btn-warning">İptal</a>
</form>
</div>
{% endblock %}
""", cat=cat, cats=cats[cat])

# ----- ŞİRKETLER & DEVLET & GHETTO (Listeleme) -----
@app.route('/companies')
def companies():
    posts = Post.query.filter_by(category='companies').order_by(Post.created_at.desc()).all()
    return render_template_string(BASE_HTML + """
{% block content %}
<div class="card">
<h2>🏢 Şirketler</h2>
{% if current_user.is_authenticated and current_user.is_admin %}<a href="{{ url_for('new_post', cat='companies') }}" class="btn btn-primary">+ Ekle</a>{% endif %}
{% for p in posts %}<div class="post-item"><h4>{{ p.title }}</h4><p>{{ p.content }}</p></div>{% else %}<p>Boş.</p>{% endfor %}
</div>
{% endblock %}
""", posts=posts)

@app.route('/government')
def government():
    posts = Post.query.filter_by(category='government').order_by(Post.created_at.desc()).all()
    return render_template_string(BASE_HTML + """
{% block content %}
<div class="card">
<h2>🏛️ Devlet</h2>
{% if current_user.is_authenticated and current_user.role_level >= 30 %}<a href="{{ url_for('new_post', cat='government') }}" class="btn btn-primary">+ Ekle</a>{% endif %}
{% for p in posts %}<div class="post-item"><h4>[{{ p.subcategory }}] {{ p.title }}</h4><p>{{ p.content }}</p></div>{% else %}<p>Boş.</p>{% endfor %}
</div>
{% endblock %}
""", posts=posts)

@app.route('/ghetto')
def ghetto():
    posts = Post.query.filter_by(category='ghetto').order_by(Post.created_at.desc()).all()
    return render_template_string(BASE_HTML + """
{% block content %}
<div class="card">
<h2>⚔️ Getto</h2>
{% if current_user.is_authenticated and current_user.role_level >= 30 %}<a href="{{ url_for('new_post', cat='ghetto') }}" class="btn btn-primary">+ Ekle</a>{% endif %}
{% for p in posts %}<div class="post-item"><h4>[{{ p.subcategory }}] {{ p.title }}</h4><p>{{ p.content }}</p></div>{% else %}<p>Boş.</p>{% endfor %}
</div>
{% endblock %}
""", posts=posts)

# ----- BAŞVURULAR -----
@app.route('/applications')
def applications():
    apps = Application.query.order_by(Application.created_at.desc()).all()
    return render_template_string(BASE_HTML + """
{% block content %}
<div class="card">
<h2>📝 Başvurular</h2>
<a href="{{ url_for('new_application', app_type='liderlik') }}" class="btn btn-primary">Liderlik</a>
<a href="{{ url_for('new_application', app_type='yonetici') }}" class="btn btn-primary">Yönetici</a>
<a href="{{ url_for('new_application', app_type='asistan') }}" class="btn btn-primary">Asistan</a>
<table style="margin-top:20px;">
{% for a in apps %}
<tr><td>{{ a.applicant.username }}</td><td>{{ a.type }}</td><td>{{ a.status }}</td>
<td>{% if current_user.is_authenticated and current_user.is_admin %}
<form method="POST" action="{{ url_for('review_app', app_id=a.id) }}" style="display:flex;gap:5px;">
<select name="status"><option>Kabul</option><option>Red</option></select>
<button class="btn btn-sm btn-primary">Onayla</button>
</form>{% endif %}</td></tr>
{% endfor %}
</table>
</div>
{% endblock %}
""", apps=apps)

@app.route('/applications/new/<app_type>', methods=['GET', 'POST'])
@login_required
def new_application(app_type):
    if request.method == 'POST':
        a = Application(type=app_type, data=json.dumps(request.form.to_dict()), applicant_id=current_user.id)
        db.session.add(a); db.session.commit()
        flash('Başvurunuz alındı.', 'success')
        return redirect(url_for('applications'))
    
    fields = {
        'liderlik': ['Gerçek adınız', 'Yaşınız', 'Saat diliminiz', 'Günlük aktiflik', 'Discord', 'Oyun içi isim', 'Statik ID', 'Organizasyon', 'Neden Lider?', 'Öneriler'],
        'yonetici': ['Gerçek adınız', 'Yaşınız', 'Saat diliminiz', 'Aktif saatler', 'Günlük aktiflik', 'Discord', 'Oyun içi isim', 'Statik ID', 'Küratör (Suç/Devlet)', 'Neden Yönetici?', 'Güçlü Yönler', 'Zayıf Yönler'],
        'asistan': ['Gerçek adınız', 'Yaşınız', 'Saat diliminiz', 'Aktif saatler', 'Günlük aktiflik', 'Discord', 'Oyun içi isim', 'Statik ID', 'Neden Asistan?', 'Güçlü Yönler', 'Zayıf Yönler']
    }
    return render_template_string(BASE_HTML + """
{% block content %}
<div class="card" style="max-width:700px;margin:0 auto;">
<h2>{{ app_type|capitalize }} Başvuru Formu</h2>
<form method="POST">
{% for f in fields %}<label>{{ f }}</label><input type="text" name="{{ f }}" required>{% endfor %}
<button class="btn btn-success" type="submit">Gönder</button>
<a href="{{ url_for('applications') }}" class="btn btn-warning">İptal</a>
</form>
</div>
{% endblock %}
""", app_type=app_type, fields=fields[app_type])

@app.route('/applications/<int:app_id>/review', methods=['POST'])
@requires_role('Junior Administrator')
def review_app(app_id):
    a = Application.query.get_or_404(app_id)
    a.status = request.form.get('status')
    db.session.commit()
    return redirect(url_for('applications'))

# ----- ŞİKAYETLER -----
@app.route('/complaints')
def complaints():
    comps = Complaint.query.order_by(Complaint.created_at.desc()).all()
    return render_template_string(BASE_HTML + """
{% block content %}
<div class="card">
<h2>⚠️ Şikayetler</h2>
<a href="{{ url_for('new_complaint', comp_type='player') }}" class="btn btn-danger">Oyuncu Şikayeti</a>
<a href="{{ url_for('new_complaint', comp_type='admin') }}" class="btn btn-warning">Yönetici Şikayeti</a>
<table style="margin-top:20px;">
{% for c in comps %}
<tr><td>{{ c.complainant.username }}</td><td>{{ c.type }}</td><td>{{ c.status }}</td>
<td>{% if cur
