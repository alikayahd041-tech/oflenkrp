import os
import json
import secrets
from datetime import datetime
from functools import wraps

from flask import (Flask, request, session, redirect, url_for,
                   render_template, abort, flash)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from jinja2 import DictLoader

# ----------------------------------------------------------------- AYARLAR
SITE_NAME = "Of Leank RP"
RULES_WRITE_LEVEL = 7   # Kurallara yazabilmek için gereken minimum rol seviyesi
REVIEW_LEVEL = 3        # Şikayet/başvuru durumunu değiştirebilen minimum seviye
DELETE_LEVEL = 5        # Konu silebilen minimum seviye
ROLE_ADMIN_LEVEL = 8    # Yönetim paneli (rol atama) seviyesi

ROLES = [
    ("Project Manager", 9),
    ("Deputy Project Manager", 8),
    ("Project Coordinator", 7),
    ("Chief Administrator", 6),
    ("Deputy Chief Administrator", 5),
    ("Senior Administrator", 4),
    ("Junior Administrator", 3),
    ("The Server Administrator", 2),
    ("Admin Assistant", 1),
    ("Oyuncu", 0),
]
ROLE_LEVEL = dict(ROLES)
STATUSES = ["Beklemede", "İnceleniyor", "Kabul Edildi", "Reddedildi"]

# ------------------------------------------------------------------ FORMLAR
FORMS = {
    "player_report": {"title": "Oyuncu Şikayet Formu", "fields": [
        ("crime", "İşlediği Suç / Şikayet Edilen Kişi İsmi", "text"),
        ("nick", "Your Nick Name", "text"),
        ("static_id", "Your Static ID", "text"),
        ("date", "Date", "date"),
        ("time", "Time", "time"),
        ("proof", "Proof (video / resim linki)", "textarea")]},
    "admin_report": {"title": "Yönetici Şikayet Formu", "fields": [
        ("crime", "İşlediği Suç / Şikayet Edilen Admin", "text"),
        ("nick", "Your Nick Name", "text"),
        ("static_id", "Your Static ID", "text"),
        ("admin_nick", "Administrator Nick Name", "text"),
        ("date", "Date", "date"),
        ("time", "Time", "time"),
        ("proof", "Proof (video / resim linki)", "textarea")]},
    "leader_app": {"title": "Liderlik Başvuru Formu", "fields": [
        ("real_name", "Gerçek adınız", "text"),
        ("age", "Yaşınız", "number"),
        ("tz", "Saat diliminiz", "text"),
        ("activity", "Günlük ortalama aktiflik süreniz", "text"),
        ("discord", "Discord kullanıcı adınız", "text"),
        ("ingame", "Oyun içi isminiz", "text"),
        ("static_id", "Kalıcı oyuncu ID'niz", "text"),
        ("org", "Liderlik başvurusu yapılan organizasyon (örn. FBI, Belediye, Liberty...)", "text"),
        ("why", "Neden özellikle bu organizasyonun lideri olmak istiyorsunuz? (3 adet detaylı açıklama)", "textarea"),
        ("ideas", "Organizasyondaki RolePlay'i geliştirmek için önerileriniz nelerdir?", "textarea")]},
    "admin_app": {"title": "Yönetici Başvuru Formu", "fields": [
        ("real_name", "Gerçek adınız", "text"),
        ("age", "Yaşınız", "number"),
        ("tz", "Saat diliminiz", "text"),
        ("hours", "Sunucu saatine göre hangi saatler arasında aktifsiniz? (Örnek: 10:00 - 19:00)", "text"),
        ("activity", "Günlük ortalama aktiflik süreniz (saat olarak)", "text"),
        ("discord", "Discord kullanıcı adınız", "text"),
        ("ingame", "Oyun içi isminiz", "text"),
        ("static_id", "Oyuncu ID'niz (Menü > Profil kısmında)", "text"),
        ("area", "Hangi bölümün küratörü (yetkilisi) olmak istiyorsunuz?", "select:Suç,Devlet"),
        ("why", "Neden bir yönetici olmak istiyorsunuz?", "textarea"),
        ("strong", "Güçlü yönleriniz nelerdir?", "textarea"),
        ("weak", "En büyük zayıf yönleriniz nelerdir?", "textarea"),
        ("ready", "RP hayatından çıkıp sadece yönetici olmaya hazır mısınız?", "textarea"),
        ("problem", "Şu anda aktif olmanızı engelleyen gerçek hayata dair bir probleminiz var mı?", "textarea")]},
    "assistant_app": {"title": "Asistan Başvuru Formu", "fields": [
        ("real_name", "Gerçek adınız", "text"),
        ("age", "Yaşınız", "number"),
        ("tz", "Saat diliminiz", "text"),
        ("hours", "Sunucu saatine göre hangi saatler arasında aktifsiniz? (Örnek: 10:00 - 19:00)", "text"),
        ("activity", "Günlük ortalama aktiflik süreniz (saat olarak)", "text"),
        ("discord", "Discord kullanıcı adınız", "text"),
        ("ingame", "Oyun içi isminiz", "text"),
        ("static_id", "Oyuncu ID'niz (Menü > Profil kısmında)", "text"),
        ("why", "Neden asistan olmak istiyorsunuz?", "textarea"),
        ("strong", "Güçlü yönleriniz nelerdir?", "textarea"),
        ("weak", "En büyük zayıf yönleriniz nelerdir?", "textarea"),
        ("problem", "Şu anda aktif olmanızı engelleyen gerçek hayata dair bir probleminiz var mı?", "textarea")]},
}

# --------------------------------------------------------------- KATEGORİLER
# (section, slug, name, write: admin|player|leader, form_key, private, view_level)
CATEGORIES = [
    ("Sunucu Kuralları", "genel-kurallar", "Genel Kurallar", "admin", None, False, 0),
    ("Sunucu Kuralları", "devlet-kurallari", "Devlet Kuralları", "admin", None, False, 0),
    ("Sunucu Kuralları", "liderlik-kurallari", "Liderlik Kuralları", "admin", None, False, 0),
    ("Sunucu Kuralları", "yesil-bolge-kurallari", "Yeşil Bölge Kuralları", "admin", None, False, 0),
    ("Şikayetler", "oyuncu-sikayetleri", "Oyuncu Hakkında Şikayetler", "player", "player_report", True, 1),
    ("Şikayetler", "yonetici-sikayetleri", "Yönetici ve Yardımcı Hakkında Şikayetler", "player", "admin_report", True, 5),
    ("Başvurular", "liderlik-basvuru", "Liderlik Başvurusu", "player", "leader_app", True, 5),
    ("Başvurular", "yonetici-basvuru", "Yönetici Başvurusu", "player", "admin_app", True, 5),
    ("Başvurular", "asistan-basvuru", "Asistan Başvurusu", "player", "assistant_app", True, 3),
    ("Devlet Kurumları", "hastane", "Hastane", "leader", None, False, 0),
    ("Devlet Kurumları", "ordu", "Ordu", "leader", None, False, 0),
    ("Devlet Kurumları", "sehir-polisi", "Şehir Polisi", "leader", None, False, 0),
    ("Devlet Kurumları", "fbi", "FBI", "leader", None, False, 0),
    ("Devlet Kurumları", "medya", "Medya", "leader", None, False, 0),
    ("Devlet Kurumları", "belediye", "Belediye", "leader", None, False, 0),
    ("Getto", "fangs", "Fangs", "leader", None, False, 0),
    ("Getto", "wolves", "Wolves", "leader", None, False, 0),
    ("Getto", "rawens", "Rawens", "leader", None, False, 0),
]

# --------------------------------------------------------------------- APP
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "degistir-beni-render-env")
db_url = os.environ.get("DATABASE_URL", "sqlite:///forum.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    pw = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(40), default="Oyuncu")
    leader_of = db.Column(db.String(300), default="")  # slug'lar, virgülle
    created = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def level(self):
        return ROLE_LEVEL.get(self.role, 0)

    @property
    def is_staff(self):
        return self.level >= 1

    def leads(self, slug):
        return slug in [s.strip() for s in (self.leader_of or "").split(",")] \
            or "*" in (self.leader_of or "")


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    section = db.Column(db.String(80))
    slug = db.Column(db.String(80), unique=True)
    name = db.Column(db.String(120))
    write = db.Column(db.String(10))
    form_key = db.Column(db.String(30))
    private = db.Column(db.Boolean, default=False)
    view_level = db.Column(db.Integer, default=0)
    position = db.Column(db.Integer, default=0)


class Thread(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"))
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    title = db.Column(db.String(200))
    body = db.Column(db.Text, default="")
    data = db.Column(db.Text, default="")
    status = db.Column(db.String(30), default="")
    pinned = db.Column(db.Boolean, default=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.relationship("Category")
    author = db.relationship("User")
    posts = db.relationship("Post", backref="thread", order_by="Post.id",
                            cascade="all, delete-orphan")


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey("thread.id"))
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    body = db.Column(db.Text)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship("User")


def seed():
    db.create_all()
    for i, (sec, slug, name, write, fk, priv, vl) in enumerate(CATEGORIES):
        if not Category.query.filter_by(slug=slug).first():
            db.session.add(Category(section=sec, slug=slug, name=name, write=write,
                                    form_key=fk, private=priv, view_level=vl, position=i))
    db.session.commit()


# --------------------------------------------------------------- YARDIMCILAR
def current_user():
    uid = session.get("uid")
    return db.session.get(User, uid) if uid else None


def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if not current_user():
            flash("Önce giriş yapmalısın.")
            return redirect(url_for("login"))
        return f(*a, **k)
    return w


def can_post(user, cat):
    if not user:
        return False
    if cat.write == "player":
        return True
    if cat.write == "admin":
        return user.level >= RULES_WRITE_LEVEL
    if cat.write == "leader":
        return user.is_staff or user.leads(cat.slug)
    return False


def can_view(user, thread):
    cat = thread.category
    if not cat.private:
        return True
    if not user:
        return False
    return user.id == thread.author_id or user.level >= max(cat.view_level, 1)


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


@app.before_request
def check_csrf():
    if request.method == "POST":
        if request.form.get("csrf") != session.get("csrf"):
            abort(400)


@app.context_processor
def inject():
    return dict(me=current_user(), csrf=csrf_token, SITE=SITE_NAME, ROLES=ROLES,
                STATUSES=STATUSES, REVIEW_LEVEL=REVIEW_LEVEL, DELETE_LEVEL=DELETE_LEVEL,
                ROLE_ADMIN_LEVEL=ROLE_ADMIN_LEVEL, can_post=can_post, FORMS=FORMS)


# ------------------------------------------------------------------ ROUTES
@app.route("/")
def index():
    cats = Category.query.order_by(Category.position).all()
    sections = {}
    for c in cats:
        sections.setdefault(c.section, []).append(c)
    counts = {c.id: Thread.query.filter_by(category_id=c.id).count() for c in cats}
    return render_template("index.html", sections=sections, counts=counts)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        u = request.form["username"].strip()
        p = request.form["password"]
        if len(u) < 3 or len(p) < 6:
            flash("Kullanıcı adı en az 3, şifre en az 6 karakter olmalı.")
        elif User.query.filter(db.func.lower(User.username) == u.lower()).first():
            flash("Bu kullanıcı adı alınmış.")
        else:
            first = User.query.count() == 0
            user = User(username=u, pw=generate_password_hash(p),
                        role="Project Manager" if first else "Oyuncu")
            db.session.add(user)
            db.session.commit()
            session["uid"] = user.id
            return redirect(url_for("index"))
    return render_template("auth.html", mode="register")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter(db.func.lower(User.username) ==
                                 request.form["username"].strip().lower()).first()
        if user and check_password_hash(user.pw, request.form["password"]):
            session["uid"] = user.id
            return redirect(url_for("index"))
        flash("Kullanıcı adı veya şifre hatalı.")
    return render_template("auth.html", mode="login")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/c/<slug>")
def category(slug):
    cat = Category.query.filter_by(slug=slug).first_or_404()
    user = current_user()
    q = Thread.query.filter_by(category_id=cat.id).order_by(Thread.pinned.desc(), Thread.id.desc())
    threads = [t for t in q.all() if can_view(user, t)]
    return render_template("category.html", cat=cat, threads=threads)


@app.route("/c/<slug>/new", methods=["GET", "POST"])
@login_required
def new_thread(slug):
    cat = Category.query.filter_by(slug=slug).first_or_404()
    user = current_user()
    if not can_post(user, cat):
        abort(403)
    form = FORMS.get(cat.form_key) if cat.form_key else None
    if request.method == "POST":
        if form:
            data = {k: request.form.get(k, "").strip() for k, _, _ in form["fields"]}
            if not all(data.values()):
                flash("Tüm alanları doldurmalısın.")
                return render_template("new.html", cat=cat, form=form, vals=data)
            who = data.get("nick") or data.get("ingame") or user.username
            t = Thread(category_id=cat.id, author_id=user.id,
                       title=f"{form['title']} - {who}"[:200],
                       data=json.dumps(data, ensure_ascii=False), status=STATUSES[0])
        else:
            title = request.form.get("title", "").strip()
            body = request.form.get("body", "").strip()
            if not title or not body:
                flash("Başlık ve içerik boş olamaz.")
                return render_template("new.html", cat=cat, form=None, vals=request.form)
            t = Thread(category_id=cat.id, author_id=user.id, title=title[:200], body=body)
        db.session.add(t)
        db.session.commit()
        return redirect(url_for("thread", tid=t.id))
    return render_template("new.html", cat=cat, form=form, vals={})


@app.route("/t/<int:tid>", methods=["GET", "POST"])
def thread(tid):
    t = db.session.get(Thread, tid) or abort(404)
    user = current_user()
    if not can_view(user, t):
        abort(403)
    if request.method == "POST":
        if not user:
            return redirect(url_for("login"))
        body = request.form.get("body", "").strip()
        if body:
            db.session.add(Post(thread_id=t.id, author_id=user.id, body=body))
            db.session.commit()
        return redirect(url_for("thread", tid=t.id) + "#son")
    data = json.loads(t.data) if t.data else None
    labels = {k: l for k, l, _ in FORMS[t.category.form_key]["fields"]} if data else {}
    return render_template("thread.html", t=t, data=data, labels=labels)


@app.route("/t/<int:tid>/status", methods=["POST"])
@login_required
def set_status(tid):
    t = db.session.get(Thread, tid) or abort(404)
    if current_user().level < REVIEW_LEVEL:
        abort(403)
    s = request.form.get("status")
    if s in STATUSES:
        t.status = s
        db.session.add(Post(thread_id=t.id, author_id=current_user().id,
                            body=f"[SİSTEM] Durum güncellendi: {s}"))
        db.session.commit()
    return redirect(url_for("thread", tid=tid))


@app.route("/t/<int:tid>/pin", methods=["POST"])
@login_required
def pin(tid):
    t = db.session.get(Thread, tid) or abort(404)
    if current_user().level < DELETE_LEVEL:
        abort(403)
    t.pinned = not t.pinned
    db.session.commit()
    return redirect(url_for("thread", tid=tid))


@app.route("/t/<int:tid>/delete", methods=["POST"])
@login_required
def delete_thread(tid):
    t = db.session.get(Thread, tid) or abort(404)
    if current_user().level < DELETE_LEVEL:
        abort(403)
    slug = t.category.slug
    db.session.delete(t)
    db.session.commit()
    return redirect(url_for("category", slug=slug))


@app.route("/ekip")
def team():
    staff = User.query.filter(User.role != "Oyuncu").all()
    staff.sort(key=lambda u: -u.level)
    leaders = User.query.filter(User.leader_of != "").all()
    return render_template("team.html", staff=staff, leaders=leaders)


@app.route("/panel", methods=["GET", "POST"])
@login_required
def panel():
    if current_user().level < ROLE_ADMIN_LEVEL:
        abort(403)
    if request.method == "POST":
        u = db.session.get(User, int(request.form["uid"])) or abort(404)
        role = request.form.get("role")
        # Kendi seviyenden yüksek rol veremezsin
        if role in ROLE_LEVEL and ROLE_LEVEL[role] <= current_user().level:
            u.role = role
        u.leader_of = request.form.get("leader_of", "").strip()
        db.session.commit()
        flash(f"{u.username} güncellendi.")
        return redirect(url_for("panel"))
    users = User.query.order_by(User.id).all()
    cats = Category.query.filter_by(write="leader").all()
    return render_template("panel.html", users=users, cats=cats)


# --------------------------------------------------------------- ŞABLONLAR
BASE = """<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{% block title %}{{ SITE }}{% endblock %}</title>
<style>
:root{--bg:#0e1116;--card:#171c24;--line:#262d38;--tx:#e6e9ef;--mut:#8b94a3;--ac:#e0a526}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.5 system-ui,sans-serif}
a{color:var(--ac);text-decoration:none}a:hover{text-decoration:underline}
header{background:var(--card);border-bottom:1px solid var(--line);padding:12px 16px;display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between}
header .brand{font-size:20px;font-weight:700}nav{display:flex;gap:14px;flex-wrap:wrap;align-items:center}
main{max-width:900px;margin:0 auto;padding:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;margin-bottom:16px;overflow:hidden}
.card h2{margin:0;padding:10px 14px;font-size:14px;text-transform:uppercase;letter-spacing:.05em;color:var(--ac);border-bottom:1px solid var(--line)}
.row{display:flex;justify-content:space-between;gap:10px;padding:11px 14px;border-bottom:1px solid var(--line)}
.row:last-child{border:0}.mut{color:var(--mut);font-size:13px}
input,textarea,select{width:100%;background:#0b0e13;color:var(--tx);border:1px solid var(--line);border-radius:6px;padding:9px;font:inherit}
textarea{min-height:100px}label{display:block;margin:12px 0 4px;font-weight:600}
button,.btn{background:var(--ac);color:#111;border:0;border-radius:6px;padding:9px 16px;font-weight:700;cursor:pointer;display:inline-block}
.btn.sec{background:var(--line);color:var(--tx)}.btn.red{background:#c0392b;color:#fff}
.flash{background:#3a2c0b;border:1px solid var(--ac);padding:10px;border-radius:6px;margin-bottom:14px}
.badge{font-size:12px;padding:2px 8px;border-radius:99px;background:var(--line)}
.b-Kabul{background:#1e6b3a}.b-Red{background:#8a2a22}.b-İnc{background:#1f4f85}
.body{white-space:pre-wrap;word-break:break-word}
table{width:100%;border-collapse:collapse}td{padding:8px 14px;border-bottom:1px solid var(--line);vertical-align:top}td:first-child{width:40%;color:var(--mut)}
.inline{display:inline}.pad{padding:14px}
</style></head><body>
<header><a class="brand" href="/">{{ SITE }} Forum</a>
<nav><a href="/">Ana Sayfa</a><a href="/ekip">Yönetim Ekibi</a>
{% if me %}{% if me.level >= ROLE_ADMIN_LEVEL %}<a href="/panel">Panel</a>{% endif %}
<span class="mut">{{ me.username }} · {{ me.role }}</span>
<form class="inline" method="post" action="/logout"><input type="hidden" name="csrf" value="{{ csrf() }}"><button class="btn sec">Çıkış</button></form>
{% else %}<a href="/login">Giriş</a><a href="/register">Kayıt Ol</a>{% endif %}</nav></header>
<main>{% for m in get_flashed_messages() %}<div class="flash">{{ m }}</div>{% endfor %}
{% block content %}{% endblock %}</main></body></html>"""

INDEX = """{% extends "base.html" %}{% block content %}
{% for sec, cats in sections.items() %}<div class="card"><h2>{{ sec }}</h2>
{% for c in cats %}<div class="row"><a href="/c/{{ c.slug }}">{{ c.name }}</a>
<span class="mut">{{ counts[c.id] }} konu</span></div>{% endfor %}</div>{% endfor %}{% endblock %}"""

AUTH = """{% extends "base.html" %}{% block content %}
<div class="card pad"><h2 style="padding:0 0 10px">{{ 'Kayıt Ol' if mode=='register' else 'Giriş Yap' }}</h2>
<form method="post"><input type="hidden" name="csrf" value="{{ csrf() }}">
<label>Kullanıcı adı</label><input name="username" required>
<label>Şifre</label><input name="password" type="password" required>
<p><button>{{ 'Kayıt Ol' if mode=='register' else 'Giriş' }}</button></p></form></div>{% endblock %}"""

CATEGORY = """{% extends "base.html" %}{% block content %}
<p class="mut"><a href="/">Ana Sayfa</a> › {{ cat.section }} › {{ cat.name }}</p>
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
<h1 style="margin:0">{{ cat.name }}</h1>
{% if can_post(me, cat) %}<a class="btn" href="/c/{{ cat.slug }}/new">{{ 'Form Doldur' if cat.form_key else 'Yeni Konu' }}</a>
{% elif not me %}<a class="btn sec" href="/login">Giriş yap</a>{% endif %}</div>
<div class="card">{% for t in threads %}<div class="row"><div>
<a href="/t/{{ t.id }}">{% if t.pinned %}📌 {% endif %}{{ t.title }}</a>
<div class="mut">{{ t.author.username }} · {{ t.created.strftime('%d.%m.%Y %H:%M') }} · {{ t.posts|length }} yanıt</div></div>
{% if t.status %}<span class="badge b-{{ t.status[:3] }}">{{ t.status }}</span>{% endif %}</div>
{% else %}<div class="row mut">Henüz konu yok.</div>{% endfor %}</div>{% endblock %}"""

NEW = """{% extends "base.html" %}{% block content %}
<p class="mut"><a href="/c/{{ cat.slug }}">← {{ cat.name }}</a></p>
<div class="card pad"><h2 style="padding:0 0 10px">{{ form.title if form else 'Yeni Konu' }}</h2>
<form method="post"><input type="hidden" name="csrf" value="{{ csrf() }}">
{% if form %}{% for key, label, typ in form.fields %}<label>{{ label }}</label>
{% if typ == 'textarea' %}<textarea name="{{ key }}" required>{{ vals.get(key,'') }}</textarea>
{% elif typ.startswith('select:') %}<select name="{{ key }}">{% for o in typ[7:].split(',') %}<option {{ 'selected' if vals.get(key)==o }}>{{ o }}</option>{% endfor %}</select>
{% else %}<input name="{{ key }}" type="{{ typ }}" value="{{ vals.get(key,'') }}" required>{% endif %}{% endfor %}
{% else %}<label>Başlık</label><input name="title" value="{{ vals.get('title','') }}" required>
<label>İçerik</label><textarea name="body" style="min-height:240px" required>{{ vals.get('body','') }}</textarea>{% endif %}
<p><button>Gönder</button></p></form></div>{% endblock %}"""

THREAD = """{% extends "base.html" %}{% block title %}{{ t.title }}{% endblock %}{% block content %}
<p class="mut"><a href="/c/{{ t.category.slug }}">← {{ t.category.name }}</a></p>
<div class="card"><h2>{{ t.title }}{% if t.status %} <span class="badge b-{{ t.status[:3] }}">{{ t.status }}</span>{% endif %}</h2>
<div class="pad mut">{{ t.author.username }} ({{ t.author.role }}) · {{ t.created.strftime('%d.%m.%Y %H:%M') }}</div>
{% if data %}<table>{% for k, v in data.items() %}<tr><td>{{ labels.get(k, k) }}</td><td class="body">{{ v }}</td></tr>{% endfor %}</table>
{% else %}<div class="pad body">{{ t.body }}</div>{% endif %}</div>
{% if me and me.level >= REVIEW_LEVEL and t.status %}<div class="card pad"><form method="post" action="/t/{{ t.id }}/status">
<input type="hidden" name="csrf" value="{{ csrf() }}"><div style="display:flex;gap:8px">
<select name="status">{% for s in STATUSES %}<option {{ 'selected' if s==t.status }}>{{ s }}</option>{% endfor %}</select>
<button>Durumu Güncelle</button></div></form></div>{% endif %}
{% for p in t.posts %}<div class="card"><div class="pad mut">{{ p.author.username }} ·
<b>{{ p.author.role }}</b> · {{ p.created.strftime('%d.%m.%Y %H:%M') }}</div><div class="pad body" style="padding-top:0">{{ p.body }}</div></div>{% endfor %}
<div id="son"></div>
{% if me %}<div class="card pad"><form method="post"><input type="hidden" name="csrf" value="{{ csrf() }}">
<label style="margin-top:0">Yanıt yaz</label><textarea name="body" required></textarea><p><button>Gönder</button></p></form></div>
{% else %}<p><a href="/login">Yanıt yazmak için giriş yap.</a></p>{% endif %}
{% if me and me.level >= DELETE_LEVEL %}<form class="inline" method="post" action="/t/{{ t.id }}/pin"><input type="hidden" name="csrf" value="{{ csrf() }}"><button class="btn sec">Sabitle / Kaldır</button></form>
<form class="inline" method="post" action="/t/{{ t.id }}/delete" onsubmit="return confirm('Silinsin mi?')"><input type="hidden" name="csrf" value="{{ csrf() }}"><button class="btn red">Sil</button></form>{% endif %}
{% endblock %}"""

TEAM = """{% extends "base.html" %}{% block content %}
<div class="card"><h2>Yönetim Ekibi</h2>
{% for u in staff %}<div class="row"><span>{{ u.username }}</span><span class="badge">{{ u.role }}</span></div>
{% else %}<div class="row mut">Henüz yönetici yok.</div>{% endfor %}</div>
<div class="card"><h2>Liderler</h2>
{% for u in leaders %}<div class="row"><span>{{ u.username }}</span><span class="mut">{{ u.leader_of }}</span></div>
{% else %}<div class="row mut">Henüz lider yok.</div>{% endfor %}</div>{% endblock %}"""

PANEL = """{% extends "base.html" %}{% block content %}
<p class="mut">Lider slug'ları (virgülle): {% for c in cats %}<code>{{ c.slug }}</code> {% endfor %} — hepsi için <code>*</code></p>
{% for u in users %}<div class="card pad"><form method="post"><input type="hidden" name="csrf" value="{{ csrf() }}">
<input type="hidden" name="uid" value="{{ u.id }}"><b>{{ u.username }}</b>
<label>Rol</label><select name="role">{% for r, l in ROLES %}<option {{ 'selected' if r==u.role }}>{{ r }}</option>{% endfor %}</select>
<label>Lider olduğu birimler</label><input name="leader_of" value="{{ u.leader_of or '' }}" placeholder="fbi,hastane">
<p><button>Kaydet</button></p></form></div>{% endfor %}{% endblock %}"""

app.jinja_env.loader = DictLoader({
    "base.html": BASE, "index.html": INDEX, "auth.html": AUTH, "category.html": CATEGORY,
    "new.html": NEW, "thread.html": THREAD, "team.html": TEAM, "panel.html": PANEL,
})

with app.app_context():
    seed()

if __name__ == "__main__":
    app.run(debug=True)
