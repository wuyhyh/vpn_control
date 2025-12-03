from functools import wraps

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    g,
)

from .models import User

bp = Blueprint("auth", __name__)


def login_required(view):
    """简单的登录检查装饰器（只允许 admin 访问后台）"""

    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("auth.login"))

        user = User.query.get(user_id)
        if not user or not user.is_admin:
            flash("没有权限，请以管理员身份登录。", "danger")
            return redirect(url_for("auth.login"))

        g.current_user = user
        return view(*args, **kwargs)

    return wrapped


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password) or not user.is_admin:
            flash("用户名或密码错误，或不是管理员账号。", "danger")
            return render_template("login.html")

        session["user_id"] = user.id
        flash("登录成功。", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("已退出登录。", "info")
    return redirect(url_for("auth.login"))
