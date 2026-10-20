import os, sqlite3
from functools import wraps
from flask import Flask, request, redirect, url_for, session, flash, render_template_string, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-before-deploying")
DB = os.environ.get("DATABASE_PATH", "forum.db")

ROLES = [
    "Project Manager", "Deputy Project Manager", "Project Coordinator",
    "Chief Administrator", "Deputy Chief Administrator", "Senior Administrator",
    "Junior Administrator", "The Server Administrator", "Admin Assistant", "Member"
]
ADMIN_ROLES = ROLES[:-1]
LEADER_ORGS = ["Hastane", "Ordu", "Şehir Polisi", "FBI", "Medya", "Belediye"]
GETTO_ORGS = ["Fangs", "Wolves", "Ravens"]
RULE_CATEGORIES = ["Genel Kurallar", "Devlet Kuralları", "Liderlik Kuralları", "Yeşil Bölge Kuralları"]

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()

def init_db():
    with sqlite3.connect(DB) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'Member',
            lang TEXT NOT NULL DEFAULT 'tr')""")
        con.execute("""CREATE TABLE IF NOT EXISTS posts(
            id INTEGER PRIMARY KEY, kind TEXT NOT NULL, category TEXT NOT NULL,
            title TEXT NOT NULL, body TEXT NOT NULL, author TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'İnceleniyor', created TEXT DEFAULT CURRENT_TIMESTAMP)""")
        con.execute("""CREATE TABLE IF NOT EXISTS comments(
            id INTEGER PRIMARY KEY, post_id INTEGER NOT NULL, author TEXT NOT NULL,
            body TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP)""")
        con.execute("""CREATE TABLE IF NOT EXISTS rules(
            id INTEGER PRIMARY KEY, category TEXT NOT NULL, body TEXT NOT NULL,
            author TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP)""")
        con.commit()

@app.before_request
def setup():
    init_db()

def current_user():
    if "user_id" not in session:
        return None
    return db().execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()

def is_admin(user=None):
    user = user or current_user()
    return bool(user and user["role"] in ADMIN_ROLES)

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Bu işlem için giriş yapmalısın.")
            return redirect(url_for("home"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not is_admin():
            flash("Bu alan yalnızca yetkili yöneticilere açıktır.")
            return redirect(url_for("home"))
        return fn(*args, **kwargs)
    return wrapper

PAGE = r"""
<!doctype html><html lang="{{ 'ar' if lang=='ar' else 'tr' }}" dir="{{ 'rtl' if lang=='ar' else 'ltr' }}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OF LENK RP Forum</title>
<style>
:root{--bg:#080d18;--panel:#111b2d;--line:#263d5d;--blue:#1685ff;--text:#eef4ff;--muted:#aebdd2}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:Arial,sans-serif}
header{background:#0d1728;border-bottom:2px solid var(--blue);padding:20px 14px;text-align:center}
h1{margin:0;color:#58aaff;letter-spacing:2px}header p{color:var(--muted);margin:8px 0 0}
nav{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;padding:13px;background:#0b1322;position:sticky;top:0}
a,button{cursor:pointer}a{color:#76baff;text-decoration:none}button,.btn{border:0;border-radius:7px;background:var(--blue);color:white;padding:10px 13px;font-weight:700;display:inline-block}
button.secondary,.btn.secondary{background:#24354d}button.danger{background:#9f2d43}
main{max-width:980px;margin:22px auto;padding:0 13px}.hero,.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px;margin-bottom:14px}
.hero{text-align:center;padding:28px 18px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
h2,h3{color:#58aaff;margin-top:0}p{line-height:1.55;color:#d1dced}.muted,small{color:var(--muted)}
input,textarea,select{width:100%;padding:11px;margin:5px 0 12px;background:#08111f;color:white;border:1px solid #344b69;border-radius:7px}
textarea{min-height:100px;resize:vertical}label{font-size:14px;color:#c9d7e9}form{margin-top:12px}.field{margin-bottom:5px}
.status{display:inline-block;padding:5px 8px;border-radius:20px;background:#24354d;font-size:12px}
.item{border-top:1px solid var(--line);padding:13px 0}.actions{display:flex;gap:7px;flex-wrap:wrap}.flash{background:#18375a;padding:10px;border-radius:8px;margin:10px 0}
footer{text-align:center;padding:24px;color:#8ea2bd}@media(max-width:500px){h1{font-size:24px}nav{position:static}}
</style></head><body>
<header><h1>OF LENK RP</h1><p>{{ 'المنتدى الرسمي للمجتمع' if lang=='ar' else 'Resmî Topluluk Forumu' }}</p></header>
<nav>
<a class="btn secondary" href="{{url_for('home',lang=lang)}}">{{'الرئيسية' if lang=='ar' else 'Ana Sayfa'}}</a>
<a class="btn secondary" href="{{url_for('rules',lang=lang)}}">{{'القوانين' if lang=='ar' else 'Sunucu Kuralları'}}</a>
<a class="btn secondary" href="{{url_for('complaints',lang=lang)}}">{{'الشكاوى' if lang=='ar' else 'Şikâyetler'}}</a>
<a class="btn secondary" href="{{url_for('applications',lang=lang)}}">{{'التقديمات' if lang=='ar' else 'Başvurular'}}</a>
<a class="btn secondary" href="{{url_for('organizations',lang=lang)}}">{{'المنظمات' if lang=='ar' else 'Kurumlar / Getto'}}</a>
<a class="btn secondary" href="{{url_for('home',lang='tr')}}">🇹🇷 TR</a><a class="btn secondary" href="{{url_for('home',lang='ar')}}">🇸🇦 KSA</a>
{% if user %}<span class="btn secondary">{{user['username']}} · {{user['role']}}</span><a class="btn" href="{{url_for('logout')}}">{{'خروج' if lang=='ar' else 'Çıkış'}}</a>{% else %}<a class="btn" href="{{url_for('home',lang=lang)}}#auth">{{'دخول / تسجيل' if lang=='ar' else 'Giriş / Kayıt'}}</a>{% endif %}
{% if admin %}<a class="btn" href="{{url_for('admin_panel',lang=lang)}}">Yönetim Paneli</a>{% endif %}
</nav>
<main>
{% for msg in get_flashed_messages() %}<div class="flash">{{msg}}</div>{% endfor %}
{{content|safe}}
</main><footer>© 2026 OF LENK RP · Community Forum</footer></body></html>
"""

def page(content, lang=None):
    user = current_user()
    return render_template_string(PAGE, content=content, user=user, admin=is_admin(user), lang=lang or (request.args.get("lang") or (user["lang"] if user else "tr")))

@app.route("/")
def home():
    lang=request.args.get("lang","tr")
    arabic=lang=="ar"
    content=f"""
    <section class="hero"><h2>{'مرحباً بك في OF LENK RP' if arabic else 'OF LENK RP’ye Hoş Geldin!'}</h2>
    <p>{'اختر القسم المناسب وشارك في المجتمع.' if arabic else 'Şikâyet gönder, başvuru yap, kuralları incele ve toplulukla etkileşime geç.'}</p>
    <div class="actions" style="justify-content:center"><a class="btn" href="/complaints?lang={lang}">{'إرسال شكوى' if arabic else 'Şikâyet Gönder'}</a><a class="btn" href="/applications?lang={lang}">{'تقديم طلب' if arabic else 'Başvuru Yap'}</a></div></section>
    <div class="grid">
    <section class="card"><h3>{'قوانين الخادم' if arabic else '📜 Sunucu Kuralları'}</h3><p>{'القوانين العامة وقوانين الدولة والقيادة والمنطقة الخضراء.' if arabic else 'Genel, devlet, liderlik ve yeşil bölge kuralları.'}</p><a href="/rules?lang={lang}">{'عرض القوانين' if arabic else 'Kuralları Gör'}</a></section>
    <section class="card"><h3>{'الشكاوى' if arabic else '⚖️ Şikâyet Sistemi'}</h3><p>{'قدّم شكوى وتابع حالة المراجعة.' if arabic else 'Oyuncu veya yönetici hakkında şikâyet gönder, durumunu takip et.'}</p><a href="/complaints?lang={lang}">{'افتح القسم' if arabic else 'Bölümü Aç'}</a></section>
    <section class="card"><h3>{'التقديمات' if arabic else '📝 Başvurular'}</h3><p>{'قيادة، إدارة، ومساعد إدارة.' if arabic else 'Liderlik, yönetici ve asistan başvuruları.'}</p><a href="/applications?lang={lang}">{'قدّم الآن' if arabic else 'Başvuru Yap'}</a></section></div>
    <section class="card" id="auth"><h2>{'دخول / تسجيل حساب' if arabic else 'Giriş / Hesap Oluştur'}</h2>
    <p class="muted">{'أنشئ حساباً لمشاركة الشكاوى والطلبات.' if arabic else 'Şikâyet ve başvuru göndermek için hesap oluştur.'}</p>
    <div class="grid"><form method="post" action="/register"><h3>{'إنشاء حساب' if arabic else 'Kayıt Ol'}</h3><label>Kullanıcı adı</label><input name="username" required minlength="3" maxlength="30"><label>Şifre</label><input name="password" type="password" required minlength="8"><input type="hidden" name="lang" value="{lang}"><button>Kayıt Ol</button></form>
    <form method="post" action="/login"><h3>{'تسجيل الدخول' if arabic else 'Giriş Yap'}</h3><label>Kullanıcı adı</label><input name="username" required><label>Şifre</label><input name="password" type="password" required><input type="hidden" name="lang" value="{lang}"><button>Giriş Yap</button></form></div></section>
    """
    return page(content,lang)

@app.post("/register")
def register():
    username=request.form.get("username","").strip()
    password=request.form.get("password","")
    if len(username)<3 or len(password)<8:
        flash("Kullanıcı adı en az 3, şifre en az 8 karakter olmalı.")
    else:
        try:
            cur=db().execute("INSERT INTO users(username,password_hash,role,lang) VALUES(?,?,?,?)",(username,generate_password_hash(password),"Member",request.form.get("lang","tr")))
            db().commit(); session["user_id"]=cur.lastrowid; flash("Hesabın oluşturuldu.")
        except sqlite3.IntegrityError: flash("Bu kullanıcı adı zaten alınmış.")
    return redirect(url_for("home",lang=request.form.get("lang","tr")))

@app.post("/login")
def login():
    user=db().execute("SELECT * FROM users WHERE username=?",(request.form.get("username","").strip(),)).fetchone()
    if user and check_password_hash(user["password_hash"],request.form.get("password","")):
        session["user_id"]=user["id"]; flash("Giriş başarılı.")
    else: flash("Kullanıcı adı veya şifre hatalı.")
    return redirect(url_for("home",lang=request.form.get("lang","tr")))

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("home"))

@app.route("/rules")
def rules():
    lang=request.args.get("lang","tr")
    content="<section class='card'><h2>Sunucu Kuralları</h2><p>Yetkililer aşağıdaki bölümlere kural ekleyebilir. Kurallar yayımlandığında herkes görebilir.</p>"
    for cat in RULE_CATEGORIES:
        content+=f"<section class='card'><h3>{cat}</h3>"
        rows=db().execute("SELECT * FROM rules WHERE category=? ORDER BY id DESC",(cat,)).fetchall()
        if not rows: content+="<p class='muted'>Henüz kural eklenmedi.</p>"
        for r in rows: content+=f"<div class='item'><p>{r['body']}</p><small>Ekleyen: {r['author']}</small></div>"
        if is_admin(): content+=f"""<form method="post" action="/rules/add"><input type="hidden" name="category" value="{cat}"><label>Yeni kural</label><textarea name="body" required></textarea><button>Kural Ekle</button></form>"""
        content+="</section>"
    content+="</section>"
    return page(content,lang)

@app.post("/rules/add")
@admin_required
def add_rule():
    body=request.form.get("body","").strip()
    if body: db().execute("INSERT INTO rules(category,body,author) VALUES(?,?,?)",(request.form["category"],body,current_user()["username"])); db().commit(); flash("Kural eklendi.")
    return redirect(url_for("rules"))

@app.route("/complaints")
def complaints():
    lang=request.args.get("lang","tr")
    rows=db().execute("SELECT * FROM posts WHERE kind IN ('Oyuncu Şikâyeti','Yönetici Şikâyeti','Şirketler İçerikleri') ORDER BY id DESC").fetchall()
    content="""<section class="card"><h2>Şikâyetler ve Şirketler İçerikleri</h2><p>Şikâyet oluşturmak ve yorum yazmak için giriş yap. Kanıt bağlantısı veya açıklaması ekle; hassas kişisel bilgileri paylaşma.</p>"""
    if current_user():
        content+="""
        <div class="grid">
        <form method="post" action="/post"><h3>Oyuncu Hakkında Şikâyet</h3><input type="hidden" name="kind" value="Oyuncu Şikâyeti"><label>İşlediği suç / Şikâyet edilen kişi ismi</label><input name="target" required><label>Your Nick Name</label><input name="nick" required><label>Your Static ID</label><input name="static_id" required><label>Date</label><input name="date" type="date" required><label>Time</label><input name="time" type="time" required><label>Proof (kanıt)</label><textarea name="proof" required></textarea><button>Şikâyeti Gönder</button></form>
        <form method="post" action="/post"><h3>Yönetici Hakkında Şikâyet</h3><input type="hidden" name="kind" value="Yönetici Şikâyeti"><label>İşlediği suç / Şikâyet edilen admin</label><input name="target" required><label>Your Nick Name</label><input name="nick" required><label>Your Static ID</label><input name="static_id" required><label>Administrator Nick Name</label><input name="admin_nick" required><label>Date</label><input name="date" type="date" required><label>Time</label><input name="time" type="time" required><label>Proof (kanıt)</label><textarea name="proof" required></textarea><button>Şikâyeti Gönder</button></form>
        </div>
        <form method="post" action="/post"><h3>Şirketler İçerikleri / Genel Paylaşım</h3><input type="hidden" name="kind" value="Şirketler İçerikleri"><label>Başlık</label><input name="title" required><label>İçerik</label><textarea name="body" required></textarea><button>Paylaş</button></form>
        """
    else: content+="<p>Şikâyet göndermek için önce giriş yap.</p>"
    content+="<h2>Gönderiler</h2>"
    for r in rows:
        content+=f"<div class='item'><h3>{r['title']}</h3><p>{r['body']}</p><small>{r['kind']} · {r['author']} · {r['created']}</small><p><span class='status'>{r['status']}</span></p>"
        if current_user():
            content+=f"""<form method="post" action="/comment"><input type="hidden" name="post_id" value="{r['id']}"><textarea name="body" placeholder="Yorum yaz..." required></textarea><button>Yorum Ekle</button></form>"""
        comments=db().execute("SELECT * FROM comments WHERE post_id=? ORDER BY id",(r["id"],)).fetchall()
        for c in comments: content+=f"<p>💬 <b>{c['author']}:</b> {c['body']}</p>"
        if is_admin():
            content+=f"""<form method="post" action="/status"><input type="hidden" name="post_id" value="{r['id']}"><select name="status"><option>İnceleniyor</option><option>Kabul Edildi</option><option>Reddedildi</option></select><button>Durumu Kaydet</button></form>"""
        content+="</div>"
    content+="</section>"
@app.route("/applications")
def applications():
    lang = request.args.get("lang", "tr")
    lang = request.args.get("lang", "tr")
    content = """
    <section class='card'>
      <h2>Başvurular</h2>
      <p>Başvuru sistemi yakında aktif olacak.</p>
    </section>
    """
    return page(content, lang)


@app.route("/organizations")
def organizations():
    lang = request.args.get("lang", "tr")
    lang = request.args.get("lang", "tr")
    content = """
    <section class='card'>
      <h2>Devlet Kurumları</h2>
      <p>Kurum duyuruları yakında aktif olacak.</p>
    </section>
    """
    return page(content, lang)
