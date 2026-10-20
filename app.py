import os
from datetime import datetime, timezone
from functools import wraps

from authlib.integrations.flask_client import OAuth
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-this-secret")
db_url = os.getenv("DATABASE_URL", "sqlite:///off_leank_local.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

db = SQLAlchemy(app)
oauth = OAuth(app)
google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

ROLES = [
    "Member", "Admin Assistant", "The Server Administrator", "Junior Administrator",
    "Senior Administrator", "Deputy Chief Administrator", "Chief Administrator",
    "Project Coordinator", "Deputy Project Manager", "Project Manager", "OWNER"
]
ROLE_LABELS = {"OWNER": "Senior Administrator (Owner)"}
ADMIN_ROLES = set(ROLES[1:])
LEADER_SECTIONS = {"Hospital", "Army", "City Police", "FBI", "Media", "Municipality",
                   "Fangs", "Wolves", "Rawens"}
RULE_CATEGORIES = ["General Rules", "State Rules", "Leadership Rules", "Green Zone Rules"]
DEPARTMENTS = ["Hospital", "Army", "City Police", "FBI", "Media", "Municipality"]
GANGS = ["Fangs", "Wolves", "Rawens"]


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_sub = db.Column(db.String(160), unique=True, nullable=False)
    email = db.Column(db.String(320), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False, default="Player")
    avatar = db.Column(db.String(500))
    role = db.Column(db.String(80), nullable=False, default="Member")
    server = db.Column(db.String(8), nullable=False, default="tr")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class Rule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server = db.Column(db.String(8), nullable=False, index=True)
    category = db.Column(db.String(80), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server = db.Column(db.String(8), nullable=False, index=True)
    kind = db.Column(db.String(20), nullable=False)  # player/admin
    crime = db.Column(db.String(500), nullable=False)
    accused = db.Column(db.String(160), nullable=False)
    reporter_nick = db.Column(db.String(160), nullable=False)
    static_id = db.Column(db.String(100), nullable=False)
    accused_admin = db.Column(db.String(160))
    complaint_date = db.Column(db.String(50), nullable=False)
    complaint_time = db.Column(db.String(50), nullable=False)
    proof = db.Column(db.Text, nullable=False)
    details = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default="reviewing")
    decision_note = db.Column(db.Text)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    server = db.Column(db.String(8), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    url = db.Column(db.String(500), nullable=False, default="/")
    read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server = db.Column(db.String(8), nullable=False, index=True)
    kind = db.Column(db.String(30), nullable=False)
    applicant_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    answers = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="reviewing")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class CommunityPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server = db.Column(db.String(8), nullable=False, index=True)
    section = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


def current_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None


def is_owner(user=None):
    user = user or current_user()
    return bool(user and user.email.lower() == os.getenv("OWNER_EMAIL", "alikayahd041@gmail.com").lower())


def role_rank(user=None):
    user = user or current_user()
    if not user:
        return 0
    if is_owner(user):
        return 100
    try:
        return ROLES.index(user.role)
    except ValueError:
        return 0


def can_moderate(user=None):
    return role_rank(user) >= 1


def can_manage_roles(user=None):
    return role_rank(user) >= ROLES.index("Project Manager") or is_owner(user)


def can_write_leader_section(user, section):
    if not user:
        return False
    if is_owner(user) or role_rank(user) >= ROLES.index("Project Coordinator"):
        return True
    # Leadership is assigned through a role name like "Leader: FBI" in production.
    return user.role == f"Leader: {section}"


def notify_user(user_id, server, title, body, target_url="/"):
    db.session.add(Notification(user_id=user_id, server=server, title=title,
                                body=body, url=target_url))


def notify_moderators(server, title, body, target_url="/"):
    moderators = User.query.filter(User.server == server).all()
    for user in moderators:
        if can_moderate(user):
            notify_user(user.id, server, title, body, target_url)


@app.before_request
def ensure_schema():
    # Suitable for this starter. For production, use migrations rather than create_all.
    if not getattr(app, "_schema_ready", False):
        db.create_all()
        app._schema_ready = True


@app.context_processor
def inject_globals():
    user = current_user()
    server = session.get("server", "tr")
    unread = Notification.query.filter_by(user_id=user.id, server=server, read=False).count() if user else 0
    return dict(me=user, server=server, is_ar=(server == "ksa"),
                can_moderate=can_moderate(user), can_manage_roles=can_manage_roles(user),
                role_label=(ROLE_LABELS.get("OWNER") if is_owner(user) else (user.role if user else "Member")),
                unread_count=unread, roles=ROLES, rule_categories=RULE_CATEGORIES,
                departments=DEPARTMENTS, gangs=GANGS)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please sign in with Google first.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def moderator_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not can_moderate():
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def owner_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_owner():
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@app.route("/choose", methods=["GET", "POST"])
def choose_server():
    if request.method == "POST":
        server = request.form.get("server")
        if server not in ("tr", "ksa"):
            abort(400)
        session["server"] = server
        user = current_user()
        if user:
            user.server = server
            db.session.commit()
        return redirect(url_for("index"))
    return render_template("choose.html")


@app.route("/")
def index():
    if not session.get("server"):
        return redirect(url_for("choose_server"))
    server = session["server"]
    rules = Rule.query.filter_by(server=server).order_by(Rule.created_at.desc()).all()
    complaints = Complaint.query.filter_by(server=server).order_by(Complaint.created_at.desc()).limit(10).all()
    posts = CommunityPost.query.filter_by(server=server).order_by(CommunityPost.created_at.desc()).limit(20).all()
    apps = Application.query.filter_by(server=server).order_by(Application.created_at.desc()).limit(10).all() if can_moderate() else []
    return render_template("index.html", rules=rules, complaints=complaints, posts=posts, applications=apps,
                           role_choices=[r for r in ROLES if r != "OWNER"])


@app.route("/login")
def login():
    if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv("GOOGLE_CLIENT_SECRET"):
        flash("Google OAuth is not configured in Render environment variables.", "error")
        return redirect(url_for("index"))
    return google.authorize_redirect(url_for("auth_callback", _external=True))


@app.route("/auth/callback")
def auth_callback():
    token = google.authorize_access_token()
    info = token.get("userinfo") or google.parse_id_token(token)
    if not info or not info.get("email") or not info.get("sub"):
        abort(400, "Google did not return a verified user identity.")
    if not info.get("email_verified", False):
        abort(403, "Please use a verified Google email.")
    email = info["email"].lower()
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(google_sub=info["sub"], email=email, name=info.get("name") or "Player",
                    avatar=info.get("picture"), role="Member", server=session.get("server", "tr"))
        db.session.add(user)
        db.session.flush()
    user.google_sub = info["sub"]
    user.name = info.get("name") or user.name
    user.avatar = info.get("picture") or user.avatar
    if is_owner(user):
        # Internal OWNER is the top permission; display label remains Senior Administrator (Owner).
        user.role = "OWNER"
    db.session.commit()
    session["user_id"] = user.id
    return redirect(request.args.get("next") or url_for("index"))


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    flash("Signed out.", "success")
    return redirect(url_for("index"))


@app.route("/rules/add", methods=["POST"])
@login_required
@moderator_required
def add_rule():
    category = request.form.get("category", "")
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    if category not in RULE_CATEGORIES or not title or not body:
        flash("Complete all rule fields.", "error")
    else:
        db.session.add(Rule(server=session["server"], category=category, title=title,
                            body=body, author_id=current_user().id))
        db.session.commit()
        flash("Rule published.", "success")
    return redirect(url_for("index") + "#rules")


@app.route("/rules/<int:rule_id>/delete", methods=["POST"])
@login_required
@moderator_required
def delete_rule(rule_id):
    rule = db.session.get(Rule, rule_id) or abort(404)
    if rule.server != session.get("server"):
        abort(404)
    db.session.delete(rule)
    db.session.commit()
    flash("Rule deleted.", "success")
    return redirect(url_for("index") + "#rules")


@app.route("/complaints/add", methods=["POST"])
@login_required
def add_complaint():
    server = session.get("server")
    kind = request.form.get("kind", "player")
    crime = request.form.get("crime", "").strip()
    accused = request.form.get("accused", "").strip()
    nick = request.form.get("reporter_nick", "").strip()
    static_id = request.form.get("static_id", "").strip()
    date = request.form.get("complaint_date", "").strip()
    time = request.form.get("complaint_time", "").strip()
    proof = request.form.get("proof", "").strip()
    accused_admin = request.form.get("accused_admin", "").strip()
    details = request.form.get("details", "").strip()
    if kind not in ("player", "admin") or not all([crime, accused, nick, static_id, date, time, proof]):
        flash("Please complete all required complaint fields.", "error")
        return redirect(url_for("index") + "#complaints")
    complaint = Complaint(server=server, kind=kind, crime=crime, accused=accused, reporter_nick=nick,
                          static_id=static_id, accused_admin=accused_admin, complaint_date=date,
                          complaint_time=time, proof=proof, details=details, reporter_id=current_user().id)
    db.session.add(complaint)
    db.session.flush()
    notify_moderators(server, "New complaint", f"Complaint #{complaint.id} needs review.", "/#complaints")
    # Confirmation for the player is also persisted.
    notify_user(current_user().id, server, "Complaint received",
                f"Your complaint #{complaint.id} was submitted and is under review.", "/#complaints")
    db.session.commit()
    flash("Complaint submitted. Staff have been notified.", "success")
    return redirect(url_for("index") + "#complaints")


@app.route("/complaints/<int:complaint_id>/status", methods=["POST"])
@login_required
@moderator_required
def complaint_status(complaint_id):
    complaint = db.session.get(Complaint, complaint_id) or abort(404)
    if complaint.server != session.get("server"):
        abort(404)
    status = request.form.get("status")
    if status not in ("reviewing", "accepted", "rejected"):
        abort(400)
    note = request.form.get("decision_note", "").strip()
    complaint.status = status
    complaint.decision_note = note
    status_text = {"reviewing": "Under review", "accepted": "Accepted", "rejected": "Rejected"}[status]
    notify_user(complaint.reporter_id, complaint.server, f"Complaint #{complaint.id}: {status_text}",
                note or f"Your complaint status is now: {status_text}.", "/#complaints")
    db.session.commit()
    flash("Status updated; the complainant has been notified.", "success")
    return redirect(url_for("index") + "#complaints")


@app.route("/applications/add", methods=["POST"])
@login_required
def add_application():
    kind = request.form.get("kind", "")
    allowed = {"leadership", "administrator", "assistant"}
    if kind not in allowed:
        abort(400)
    answers = {k: v.strip() for k, v in request.form.items() if k not in ("kind",) and v.strip()}
    if len(answers) < 4:
        flash("Please answer the application questions.", "error")
        return redirect(url_for("index") + "#applications")
    application = Application(server=session["server"], kind=kind, applicant_id=current_user().id, answers=answers)
    db.session.add(application)
    db.session.flush()
    notify_moderators(session["server"], "New application", f"A {kind} application needs review.", "/#applications")
    notify_user(current_user().id, session["server"], "Application received",
                "Your application was submitted and is awaiting review.", "/#applications")
    db.session.commit()
    flash("Application submitted.", "success")
    return redirect(url_for("index") + "#applications")


@app.route("/applications/<int:application_id>/status", methods=["POST"])
@login_required
@moderator_required
def application_status(application_id):
    application = db.session.get(Application, application_id) or abort(404)
    if application.server != session.get("server"):
        abort(404)
    status = request.form.get("status")
    if status not in ("reviewing", "accepted", "rejected"):
        abort(400)
    application.status = status
    applicant = db.session.get(User, application.applicant_id)
    if applicant:
        notify_user(applicant.id, application.server, "Application updated",
                    f"Your {application.kind} application status: {status}.", "/#applications")
    db.session.commit()
    flash("Application status updated.", "success")
    return redirect(url_for("index") + "#applications")


@app.route("/posts/add", methods=["POST"])
@login_required
def add_post():
    section = request.form.get("section", "").strip()
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    allowed_sections = set(DEPARTMENTS + GANGS + ["Companies"])
    if section not in allowed_sections or not title or not body:
        abort(400)
    if section in LEADER_SECTIONS and not can_write_leader_section(current_user(), section):
        abort(403)
    post = CommunityPost(server=session["server"], section=section, title=title,
                         body=body, author_id=current_user().id)
    db.session.add(post)
    db.session.commit()
    flash("Post published.", "success")
    return redirect(url_for("index") + "#community")


@app.route("/notifications")
@login_required
def notifications():
    items = Notification.query.filter_by(user_id=current_user().id, server=session.get("server")).order_by(Notification.created_at.desc()).limit(100).all()
    return render_template("notifications.html", items=items)


@app.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def notification_read(notification_id):
    item = db.session.get(Notification, notification_id) or abort(404)
    if item.user_id != current_user().id or item.server != session.get("server"):
        abort(403)
    item.read = True
    db.session.commit()
    return redirect(item.url or url_for("notifications"))


@app.route("/roles", methods=["POST"])
@login_required
@owner_required
def set_role():
    target_id = request.form.get("target_id", type=int)
    new_role = request.form.get("role", "")
    target = db.session.get(User, target_id) if target_id else None
    if not target or new_role not in [r for r in ROLES if r != "OWNER"]:
        abort(400)
    if is_owner(target):
        abort(403, "Owner role cannot be changed.")
    target.role = new_role
    db.session.commit()
    flash(f"Role updated for {target.email}.", "success")
    return redirect(url_for("index") + "#roles")


@app.route("/health")
def health():
    return {"ok": True}


@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="You do not have permission for this action."), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="Page or item not found."), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
