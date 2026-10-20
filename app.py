import os
import html
import sqlite3
from functools import wraps
from flask import (
    Flask, request, redirect, url_for,
    session, flash, render_template_string, g
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret")
DB = os.environ.get("DATABASE_PATH", "forum.db")

ROLES = [
    "Project Manager",
    "Deputy Project Manager",
    "Project Coordinator",
    "Chief Administrator",
    "Deputy Chief Administrator",
    "Senior Administrator",
    "Junior Administrator",
    "The Server Administrator",
    "Admin Assistant",
    "Member",
]
ADMIN_ROLES = ROLES[:-1]

ORGS = [
    "Hastane", "Ordu", "Şehir Polisi",
    "FBI", "Medya", "Belediye",
    "Fangs", "Wolves", "Ravens",
]
RULE_CATEGORIES = [
    "Genel Kurallar", "Devlet Kuralları",
    "Liderlik Kuralları", "Yeşil Bölge Kuralları",
]


def esc(value):
    return html.escape(str(value or ""), quote=True)


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    with sqlite3.connect(DB) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'Member',
                lang TEXT NOT NULL DEFAULT 'tr'
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY,
                kind TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                author TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'İnceleniyor',
                created TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY,
                post_id INTEGER NOT NULL,
                author TEXT NOT NULL,
                body TEXT NOT NULL,
                created TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY,
                category TEXT NOT NULL,
                body TEXT NOT NULL,
                author TEXT NOT NULL,
                created TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.commit()


@app.before_request
def setup():
    init_db()


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db().execute(
        "SELECT * FROM users WHERE id=?", (user_id,)
    ).fetchone()


def is_admin(user=None):
    user = user or current_user()
    return bool(user and user["role"] in ADMIN_ROLES)


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Bu işlem için önce giriş yapmalısın.")
            return redirect(url_for("home"))
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not is_admin():
            flash("Bu işlem yalnızca yetkililere açıktır.")
            return redirect(url_for("home"))
        return fn(*args, **kwargs)
    return wrapper


PAGE = r"""
<!doctype html>
<html lang="{{ 'ar' if lang == 'ar' else 'tr' }}"
      dir="{{ 'rtl' if lang == 'ar' else 'ltr' }}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OF LENK RP</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#080d18;color:#eef4ff;font-family:Arial}
header{background:#0d1728;border-bottom:2px solid #1685ff;
padding:20px 12px;text-align:center}
h1,h2,h3{color:#58aaff}
nav{display:flex;gap:7px;justify-content:center;flex-wrap:wrap;
padding:12px;background:#0b1322}
a{color:#83c2ff;text-decoration:none}
button,.btn{border:0;border-radius:7px;background:#1685ff;
color:white;padding:10px 12px;display:inline-block;cursor:pointer}
.secondary{background:#24354d}
main{max-width:980px;margin:20px auto;padding:0 12px}
.card,.hero{background:#111b2d;border:1px solid #263d5d;
border-radius:12px;padding:16px;margin-bottom:14px}
.hero{text-align:center;padding:28px 16px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
input,textarea,select{width:100%;padding:11px;margin:6px 0 12px;
background:#08111f;color:white;border:1px solid #344b69;border-radius:7px}
textarea{min-height:100px}
label{color:#c9d7e9;font-size:14px}
.item{border-top:1px solid #263d5d;padding:12px 0}
.muted,small{color:#aebdd2}
.flash{background:#18375a;padding:10px;border-radius:8px;margin:10px 0}
.status{display:inline-block;padding:5px 8px;background:#24354d;border-radius:15px}
footer{text-align:center;padding:22px;color:#8ea2bd}
@media(max-width:500px){h1{font-size:24px}}
</style>
</head>
<body>
<header>
<h1>OF LENK RP</h1>
<p>{{ 'المنتدى الرسمي للمجتمع' if lang == 'ar' else 'Resmî Topluluk Forumu' }}</p>
</header>
<nav>
<a class="btn secondary" href="{{url_for('home',lang=lang)}}">{{'الرئيسية' if lang=='ar' else 'Ana Sayfa'}}</a>
<a class="btn secondary" href="{{url_for('forum',lang=lang)}}">{{'المنتدى' if lang=='ar' else 'Forum'}}</a>
<a class="btn secondary" href="{{url_for('rules',lang=lang)}}">{{'القوانين' if lang=='ar' else 'Kurallar'}}</a>
<a class="btn secondary" href="{{url_for('complaints',lang=lang)}}">{{'الشكاوى' if lang=='ar' else 'Şikâyetler'}}</a>
<a class="btn secondary" href="{{url_for('applications',lang=lang)}}">{{'التقديمات' if lang=='ar' else 'Başvurular'}}</a>
<a class="btn secondary" href="{{url_for('organizations',lang=lang)}}">{{'المنظمات' if lang=='ar' else 'Kurumlar'}}</a>
<a class="btn secondary" href="{{url_for('home',lang='tr')}}">🇹🇷 TR</a>
<a class="btn secondary" href="{{url_for('home',lang='ar')}}">🇸🇦 KSA</a>
{% if user %}
<span class="btn secondary">{{user['username']}} · {{user['role']}}</span>
<a class="btn" href="{{url_for('logout')}}">{{'خروج' if lang=='ar' else 'Çıkış'}}</a>
{% else %}
<a class="btn" href="{{url_for('home',lang=lang)}}#auth">{{'دخول / تسجيل' if lang=='ar' else 'Giriş / Kayıt'}}</a>
{% endif %}
{% if admin %}
<a class="btn" href="{{url_for('admin_panel',lang=lang)}}">Yönetim Paneli</a>
{% endif %}
</nav>
<main>
{% for msg in get_flashed_messages() %}
<div class="flash">{{msg}}</div>
{% endfor %}
{{content|safe}}
</main>
<footer>© 2026 OF LENK RP · Community Forum</footer>
</body>
</html>
"""


def page(content, lang=None):
    lang = lang or request.args.get("lang", "tr")
    if lang not in ("tr", "ar"):
        lang = "tr"
    user = current_user()
    return render_template_string(
        PAGE, content=content, user=user,
        admin=is_admin(user), lang=lang
    )


def lang_redirect(endpoint, lang=None):
    return redirect(url_for(endpoint, lang=lang or request.form.get("lang", "tr")))


@app.route("/")
def home():
    lang = request.args.get("lang", "tr")
    arabic = lang == "ar"
    content = f"""
    <section class="hero">
      <h2>{'مرحباً بك في OF LENK RP' if arabic else 'OF LENK RP’ye Hoş Geldin!'}</h2>
      <p>{'اختر القسم المناسب وشارك في المجتمع.' if arabic else 'Forum konularını incele, başvuru yap ve şikâyet gönder.'}</p>
      <a class="btn" href="/forum?lang={lang}">{'المنتدى' if arabic else 'Foruma Git'}</a>
      <a class="btn" href="/applications?lang={lang}">{'التقديمات' if arabic else 'Başvuru Yap'}</a>
    </section>
    <div class="grid">
      <section class="card"><h3>📜 Kurallar</h3><p>Sunucu kurallarını incele.</p><a href="/rules?lang={lang}">Aç</a></section>
      <section class="card"><h3>⚖️ Şikâyetler</h3><p>Şikâyet oluştur ve durumunu takip et.</p><a href="/complaints?lang={lang}">Aç</a></section>
      <section class="card"><h3>🏢 Kurumlar</h3><p>Kurum duyurularını görüntüle.</p><a href="/organizations?lang={lang}">Aç</a></section>
    </div>
    <section class="card" id="auth">
      <h2>{'دخول / تسجيل حساب' if arabic else 'Giriş / Hesap Oluştur'}</h2>
      <div class="grid">
        <form method="post" action="/register">
          <h3>Kayıt Ol</h3>
          <input type="hidden" name="lang" value="{esc(lang)}">
          <label>Kullanıcı adı</label>
          <input name="username" minlength="3" maxlength="30" required>
          <label>Şifre (en az 8 karakter)</label>
          <input name="password" type="password" minlength="8" required>
          <button>Hesap Oluştur</button>
        </form>
        <form method="post" action="/login">
          <h3>Giriş Yap</h3>
          <input type="hidden" name="lang" value="{esc(lang)}">
          <label>Kullanıcı adı</label><input name="username" required>
          <label>Şifre</label><input name="password" type="password" required>
          <button>Giriş Yap</button>
        </form>
      </div>
    </section>
    """
    return page(content, lang)


@app.post("/register")
def register():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    lang = request.form.get("lang", "tr")
    if len(username) < 3 or len(username) > 30 or len(password) < 8:
        flash("Kullanıcı adı 3-30, şifre en az 8 karakter olmalı.")
        return lang_redirect("home", lang)

    admin_name = os.environ.get("ADMIN_USERNAME", "").strip()
    role = "Project Manager" if admin_name and username == admin_name else "Member"
    try:
        cur = db().execute(
            "INSERT INTO users(username,password_hash,role,lang) VALUES(?,?,?,?)",
            (username, generate_password_hash(password), role, lang)
        )
        db().commit()
        session["user_id"] = cur.lastrowid
        flash("Hesabın oluşturuldu.")
    except sqlite3.IntegrityError:
        flash("Bu kullanıcı adı zaten alınmış.")
    return lang_redirect("home", lang)


@app.post("/login")
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    lang = request.form.get("lang", "tr")
    user = db().execute(
        "SELECT * FROM users WHERE username=?", (username,)
    ).fetchone()

    if user and check_password_hash(user["password_hash"], password):
        admin_name = os.environ.get("ADMIN_USERNAME", "").strip()
        if admin_name and username == admin_name and user["role"] != "Project Manager":
            db().execute(
                "UPDATE users SET role='Project Manager' WHERE id=?",
                (user["id"],)
            )
            db().commit()
        session["user_id"] = user["id"]
        flash("Giriş başarılı.")
    else:
        flash("Kullanıcı adı veya şifre hatalı.")
    return lang_redirect("home", lang)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/forum")
def forum():
    lang = request.args.get("lang", "tr")
    rows = db().execute(
        "SELECT * FROM posts WHERE kind='Forum Konusu' ORDER BY id DESC"
    ).fetchall()
    content = "<section class='card'><h2>Topluluk Forumu</h2>"
    if current_user():
        content += """
        <form method="post" action="/post">
        <input type="hidden" name="kind" value="Forum Konusu">
        <input type="hidden" name="lang" value="LANG">
        <label>Konu başlığı</label><input name="title" maxlength="120" required>
        <label>Konu içeriği</label><textarea name="body" maxlength="8000" required></textarea>
        <button>Konu Aç</button></form>
        """.replace("LANG", esc(lang))
    else:
        content += "<p>Konu açmak için giriş yap.</p>"
    content += "</section><section class='card'><h2>Konular</h2>"
    content += render_posts(rows)
    content += "</section>"
    return page(content, lang)


def render_posts(rows):
    content = ""
    for r in rows:
        content += (
            f"<div class='item'><h3>{esc(r['title'])}</h3>"
            f"<p>{esc(r['body']).replace(chr(10), '<br>')}</p>"
            f"<small>{esc(r['kind'])} · {esc(r['author'])} · {esc(r['created'])}</small>"
            f"<p><span class='status'>{esc(r['status'])}</span></p>"
            f"<a href='/post/{r['id']}'>Konuyu Gör / Yorumlar</a></div>"
        )
    if not rows:
        content += "<p>Henüz paylaşım yok.</p>"
    return content


@app.route("/post/<int:post_id>")
def post_detail(post_id):
    lang = request.args.get("lang", "tr")
    row = db().execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
    if not row:
        return "Gönderi bulunamadı.", 404
    comments = db().execute(
        "SELECT * FROM comments WHERE post_id=? ORDER BY id",
        (post_id,)
    ).fetchall()
    content = (
        f"<section class='card'><h2>{esc(row['title'])}</h2>"
        f"<p>{esc(row['body']).replace(chr(10), '<br>')}</p>"
        f"<small>{esc(row['kind'])} · {esc(row['author'])} · {esc(row['created'])}</small>"
        f"<p><span class='status'>{esc(row['status'])}</span></p>"
        "<h3>Yorumlar</h3>"
    )
    for c in comments:
        content += f"<div class='item'><b>{esc(c['author'])}</b><p>{esc(c['body'])}</p></div>"
    if current_user():
        content += f"""
        <form method="post" action="/comment">
        <input type="hidden" name="post_id" value="{post_id}">
        <input type="hidden" name="lang" value="{esc(lang)}">
        <textarea name="body" maxlength="3000" required placeholder="Yorum yaz"></textarea>
        <button>Yorum Ekle</button></form>
        """
    content += "</section>"
    return page(content, lang)


@app.post("/post")
@login_required
def create_post():
    user = current_user()
    kind = request.form.get("kind", "Forum Konusu")
    lang = request.form.get("lang", "tr")
    allowed = {
        "Forum Konusu", "Oyuncu Şikâyeti", "Yönetici Şikâyeti",
        "Başvuru", "Kurum Duyurusu", "Şirketler İçerikleri"
    }
    if kind not in allowed:
        flash("Geçersiz gönderi türü.")
        return lang_redirect("home", lang)

    category = request.form.get("category", "").strip()[:80]
    if kind == "Oyuncu Şikâyeti":
        title = "Oyuncu Şikâyeti: " + request.form.get("target", "").strip()
        body = (
            "Şikâyet edilen: " + request.form.get("target", "").strip()
            + "\nŞikâyetçi: " + request.form.get("nick", "").strip()
            + "\nStatic ID: " + request.form.get("static_id", "").strip()
            + "\nTarih: " + request.form.get("date", "").strip()
            + "\nSaat: " + request.form.get("time", "").strip()
            + "\nKanıt / Açıklama: " + request.form.get("proof", "").strip()
        )
    elif kind == "Yönetici Şikâyeti":
        title = "Yönetici Şikâyeti: " + request.form.get("target", "").strip()
        body = (
            "Şikâyet edilen yönetici: " + request.form.get("target", "").strip()
            + "\nŞikâyetçi: " + request.form.get("nick", "").strip()
            + "\nStatic ID: " + request.form.get("static_id", "").strip()
            + "\nYönetici kullanıcı adı: " + request.form.get("admin_nick", "").strip()
            + "\nTarih: " + request.form.get("date", "").strip()
            + "\nSaat: " + request.form.get("time", "").strip()
            + "\nKanıt / Açıklama: " + request.form.get("proof", "").strip()
        )
    else:
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()

    if not title or not body:
        flash("Başlık ve açıklama boş olamaz.")
        return lang_redirect("home", lang)
    if len(title) > 120 or len(body) > 8000:
        flash("Başlık veya açıklama çok uzun.")
        return lang_redirect("home", lang)

    db().execute(
        "INSERT INTO posts(kind,category,title,body,author) VALUES(?,?,?,?,?)",
        (kind, category, title, body, user["username"])
    )
    db().commit()
    flash("Gönderin kaydedildi.")
    if kind == "Başvuru":
        return lang_redirect("applications", lang)
    if kind in ("Oyuncu Şikâyeti", "Yönetici Şikâyeti", "Şirketler İçerikleri"):
        return lang_redirect("complaints", lang)
    if kind == "Kurum Duyurusu":
        return lang_redirect("organizations", lang)
    return lang_redirect("forum", lang)


@app.post("/comment")
@login_required
def add_comment():
    post_id = request.form.get("post_id", type=int)
    body = request.form.get("body", "").strip()
    lang = request.form.get("lang", "tr")
    exists = db().execute("SELECT id FROM posts WHERE id=?", (post_id,)).fetchone()
    if not exists or not body or len(body) > 3000:
        flash("Yorum gönderilemedi.")
    else:
        db().execute(
            "INSERT INTO comments(post_id,author,body) VALUES(?,?,?)",
            (post_id, current_user()["username"], body)
        )
        db().commit()
        flash("Yorum eklendi.")
    if post_id:
        return redirect(url_for("post_detail", post_id=post_id, lang=lang))
    return lang_redirect("forum", lang)


@app.route("/complaints")
def complaints():
    lang = request.args.get("lang", "tr")
    kinds = ("Oyuncu Şikâyeti", "Yönetici Şikâyeti", "Şirketler İçerikleri")
    placeholders = ",".join("?" for _ in kinds)
    rows = db().execute(
        f"SELECT * FROM posts WHERE kind IN ({placeholders}) ORDER BY id DESC",
        kinds
    ).fetchall()

    content = """
    <section class="card"><h2>Şikâyetler ve Şirketler İçerikleri</h2>
    <p>Şikâyet gönderirken doğru bilgi ve kanıt ekle. Gereksiz kişisel bilgileri paylaşma.</p>
    """
    if current_user():
        content += """
        <div class="grid">
        <form method="post" action="/post">
        <input type="hidden" name="kind" value="Oyuncu Şikâyeti">
        <input type="hidden" name="lang" value="LANG">
        <h3>Oyuncu Şikâyeti</h3>
        <label>Şikâyet edilen kişi</label><input name="target" required>
        <label>Kendi kullanıcı adın</label><input name="nick" required>
        <label>Static ID</label><input name="static_id" required>
        <label>Tarih</label><input name="date" type="date" required>
        <label>Saat</label><input name="time" type="time" required>
        <label>Kanıt / Açıklama</label><textarea name="proof" required></textarea>
        <button>Şikâyeti Gönder</button></form>

        <form method="post" action="/post">
        <input type="hidden" name="kind" value="Yönetici Şikâyeti">
        <input type="hidden" name="lang" value="LANG">
        <h3>Yönetici Şikâyeti</h3>
        <label>Şikâyet edilen yönetici</label><input name="target" required>
        <label>Kendi kullanıcı adın</label><input name="nick" required>
        <label>Static ID</label><input name="static_id" required>
        <label>Yönetici kullanıcı adı</label><input name="admin_nick" required>
        <label>Tarih</label><input name="date" type="date" required>
        <label>Saat</label><input name="time" type="time" required>
        <label>Kanıt / Açıklama</label><textarea name="proof" required></textarea>
        <button>Şikâyeti Gönder</button></form>
        </div>
        <form method="post" action="/post">
        <input type="hidden" name="kind" value="Şirketler İçerikleri">
        <input type="hidden" name="lang" value="LANG">
        <h3>Şirketler İçerikleri / Genel Paylaşım</h3>
        <label>Başlık</label><input name="title" required>
        <label>İçerik</label><textarea name="body" required></textarea>
        <button>Paylaş</button></form>
        """.replace("LANG", esc(lang))
    else:
        content += "<p>Şikâyet göndermek için önce giriş yap.</p>"
    content += "</section><section class='card'><h2>Gönderiler</h2>"
    content += render_posts(rows)
    content += "</section>"
    return page(content, lang)

@app.route("/rules")
def rules():
    lang = request.args.get("lang", "tr")
    content = "<h2>Sunucu Kuralları</h2>"
    rows = db().execute("SELECT * FROM rules ORDER BY id DESC").fetchall()

    for rule in rows:
        content += f"<div class='card'><p>{esc(rule['body'])}</p></div>"

    return page(content, lang)
    @app.route("/organizations")
def organizations():
    lang = request.args.get("lang", "tr")
    content = """
    <div class='card'>
        <h2>Organizasyonlar</h2>
        <p>OF LENK RP organizasyonları</p>
    </div>
    """
    return page(content, lang)
@app.route("/applications")
def applications():
    lang = request.args.get("lang", "tr")
