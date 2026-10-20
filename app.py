import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fivem-rp-forum-secret-key-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///forum.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ============================================================
# YETKİ ROLLERİ (Hiyerarşik sıra)
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

def role_level(role_name):
    return ROLES.get(role_name, 0)

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
# MODELLER
# ============================================================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    static_id = db.Column(db.String(50), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(80), default='Player')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    @property
    def role_level(self):
        return role_level(self.role)

    @property
    def is_admin(self):
        return self.role_level >= role_level('Junior Administrator')


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50))  # rules, companies, government, ghetto
    subcategory = db.Column(db.String(80))
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User', backref='posts')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))  # liderlik, yonetici, asistan
    data = db.Column(db.Text)  # JSON string
    applicant_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    applicant = db.relationship('User', backref='applications')
    status = db.Column(db.String(20), default='Beklemede')  # Beklemede, Kabul, Red
    admin_note = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))  # player, admin
    data = db.Column(db.Text)  # JSON
    complainant_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    complainant = db.relationship('User', backref='complaints')
    status = db.Column(db.String(20), default='Beklemede')
    admin_note = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================================
# LOGIN MANAGER
# ============================================================
@login_manager.user_loader
def load_user(uid):
    return User.query.get(int(uid))


# ============================================================
# ROUTE'LAR
# ============================================================
@app.route('/')
def index():
    latest_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
    return render_template('index.html', latest_posts=latest_posts)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        static_id = request.form.get('static_id', '').strip()
        password = request.form.get('password', '')
        if not username or not password:
            flash('Kullanıcı adı ve şifre zorunludur.', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('Bu kullanıcı adı zaten alınmış.', 'danger')
            return redirect(url_for('register'))
        user = User(username=username, static_id=static_id, role='Player')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Kayıt başarılı! Giriş yapabilirsiniz.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f'Hoş geldin {user.username}!', 'success')
            return redirect(url_for('index'))
        flash('Hatalı kullanıcı adı veya şifre.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Çıkış yapıldı.', 'info')
    return redirect(url_for('index'))


# ------------------- KURALLAR -------------------
@app.route('/rules')
def rules():
    posts = Post.query.filter_by(category='rules').order_by(Post.created_at.desc()).all()
    return render_template('rules.html', posts=posts)


@app.route('/rules/new', methods=['GET', 'POST'])
@requires_role('Junior Administrator')
def new_rule():
    if request.method == 'POST':
        sub = request.form.get('subcategory')
        title = request.form.get('title')
        content = request.form.get('content')
        post = Post(category='rules', subcategory=sub, title=title, content=content, author_id=current_user.id)
        db.session.add(post)
        db.session.commit()
        flash('Kural eklendi.', 'success')
        return redirect(url_for('rules'))
    return render_template('new_post.html', title='Yeni Kural Ekle', categories=[
        'Genel Kurallar', 'Devlet Kuralları', 'Liderlik Kuralları', 'Yeşil Bölge Kuralları'
    ])


# ------------------- ŞİRKETLER -------------------
@app.route('/companies')
def companies():
    posts = Post.query.filter_by(category='companies').order_by(Post.created_at.desc()).all()
    return render_template('companies.html', posts=posts)


@app.route('/companies/new', methods=['GET', 'POST'])
@requires_role('Junior Administrator')
def new_company():
    if request.method == 'POST':
        post = Post(
            category='companies',
            subcategory=request.form.get('subcategory', 'Genel'),
            title=request.form.get('title'),
            content=request.form.get('content'),
            author_id=current_user.id
        )
        db.session.add(post)
        db.session.commit()
        flash('Şirket bilgisi eklendi.', 'success')
        return redirect(url_for('companies'))
    return render_template('new_post.html', title='Yeni Şirket Bilgisi', categories=['Şirketler', 'İçerikler'])


# ------------------- DEVLET -------------------
@app.route('/government')
def government():
    posts = Post.query.filter_by(category='government').order_by(Post.created_at.desc()).all()
    return render_template('government.html', posts=posts)


@app.route('/government/new', methods=['GET', 'POST'])
@requires_role('The Server Administrator')
def new_government():
    # Sadece lider rolü yazabilir (The Server Administrator üstü)
    if request.method == 'POST':
        post = Post(
            category='government',
            subcategory=request.form.get('subcategory'),
            title=request.form.get('title'),
            content=request.form.get('content'),
            author_id=current_user.id
        )
        db.session.add(post)
        db.session.commit()
        flash('Devlet kurumu bilgisi eklendi.', 'success')
        return redirect(url_for('government'))
    return render_template('new_post.html', title='Yeni Devlet Kurumu İçeriği', categories=[
        'Hastane', 'Ordu', 'Şehir Polisi', 'FBI', 'Medya', 'Belediye'
    ])


# ------------------- GHETTO -------------------
@app.route('/ghetto')
def ghetto():
    posts = Post.query.filter_by(category='ghetto').order_by(Post.created_at.desc()).all()
    return render_template('ghetto.html', posts=posts)


@app.route('/ghetto/new', methods=['GET', 'POST'])
@requires_role('The Server Administrator')
def new_ghetto():
    if request.method == 'POST':
        post = Post(
            category='ghetto',
            subcategory=request.form.get('subcategory'),
            title=request.form.get('title'),
            content=request.form.get('content'),
            author_id=current_user.id
        )
        db.session.add(post)
        db.session.commit()
        flash('Getto içeriği eklendi.', 'success')
        return redirect(url_for('ghetto'))
    return render_template('new_post.html', title='Yeni Getto İçeriği', categories=['Fangs', 'Wolves', 'Rawens'])


# ------------------- BAŞVURULAR -------------------
@app.route('/applications')
def applications():
    apps = Application.query.order_by(Application.created_at.desc()).all()
    return render_template('applications.html', applications=apps)


@app.route('/applications/new/<app_type>', methods=['GET', 'POST'])
@login_required
def new_application(app_type):
    if app_type not in ('liderlik', 'yonetici', 'asistan'):
        abort(404)

    if request.method == 'POST':
        import json
        data = {k: v for k, v in request.form.items()}
        app_obj = Application(type=app_type, data=json.dumps(data, ensure_ascii=False),
                              applicant_id=current_user.id)
        db.session.add(app_obj)
        db.session.commit()
        flash('Başvurunuz alındı!', 'success')
        return redirect(url_for('applications'))

    return render_template('new_application.html', app_type=app_type)


@app.route('/applications/<int:app_id>/review', methods=['POST'])
@requires_role('Junior Administrator')
def review_application(app_id):
    a = Application.query.get_or_404(app_id)
    a.status = request.form.get('status', 'Beklemede')
    a.admin_note = request.form.get('note', '')
    db.session.commit()
    flash('Başvuru güncellendi.', 'success')
    return redirect(url_for('applications'))


# ------------------- ŞİKAYETLER -------------------
@app.route('/complaints')
def complaints():
    comps = Complaint.query.order_by(Complaint.created_at.desc()).all()
    return render_template('complaints.html', complaints=comps)


@app.route('/complaints/new/<comp_type>', methods=['GET', 'POST'])
@login_required
def new_complaint(comp_type):
    if comp_type not in ('player', 'admin'):
        abort(404)

    if request.method == 'POST':
        import json
        data = {k: v for k, v in request.form.items()}
        c = Complaint(type=comp_type, data=json.dumps(data, ensure_ascii=False),
                      complainant_id=current_user.id)
        db.session.add(c)
        db.session.commit()
        flash('Şikayetiniz iletildi. Yöneticiler inceleyecek.', 'success')
        return redirect(url_for('complaints'))

    return render_template('new_complaint.html', comp_type=comp_type)


@app.route('/complaints/<int:comp_id>/review', methods=['POST'])
@requires_role('Junior Administrator')
def review_complaint(comp_id):
    c = Complaint.query.get_or_404(comp_id)
    c.status = request.form.get('status', 'Beklemede')
    c.admin_note = request.form.get('note', '')
    db.session.commit()
    flash('Şikayet güncellendi.', 'success')
    return redirect(url_for('complaints'))


# ------------------- ADMIN PANEL -------------------
@app.route('/admin')
@requires_role('Junior Administrator')
def admin_panel():
    return render_template('admin_panel.html',
                           users=User.query.all(),
                           applications=Application.query.all(),
                           complaints=Complaint.query.all())


@app.route('/admin/roles', methods=['GET', 'POST'])
@requires_role('Project Koordinatör')
def roles_manage():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        new_role = request.form.get('role')
        u = User.query.get(user_id)
        if u and new_role in ROLES:
            if role_level(new_role) >= role_level(current_user.role) and current_user.role != 'Project Manager':
                flash('Kendi seviyenizden yüksek rol veremezsiniz.', 'danger')
            else:
                u.role = new_role
                db.session.commit()
                flash(f'{u.username} kullanıcısının rolü {new_role} olarak güncellendi.', 'success')
        return redirect(url_for('roles_manage'))
    return render_template('roles_manage.html', users=User.query.all(), roles=list(ROLES.keys()))


# ============================================================
# BAŞLANGIÇ VERİLERİ
# ============================================================
def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', static_id='1', role='Project Manager')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('✅ Varsayılan admin oluşturuldu: admin / admin123')


init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
