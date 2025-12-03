from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)

from .models import db, User, Device
from .views_auth import login_required
from . import wireguard

bp = Blueprint("admin", __name__)


@bp.route("/")
@login_required
def dashboard():
    user_count = User.query.count()
    device_count = Device.query.count()
    return render_template(
        "admin/dashboard.html",
        user_count=user_count,
        device_count=device_count,
    )


# ---------- 用户管理 ----------

@bp.route("/users")
@login_required
def users():
    users = User.query.order_by(User.id.asc()).all()
    return render_template("admin/users.html", users=users)


@bp.route("/users/create", methods=["GET", "POST"])
@login_required
def create_user():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        is_admin = bool(request.form.get("is_admin"))

        if not username or not password:
            flash("用户名和密码不能为空。", "danger")
            return redirect(url_for("admin.create_user"))

        if User.query.filter_by(username=username).first():
            flash("用户名已存在。", "danger")
            return redirect(url_for("admin.create_user"))

        user = User(username=username, is_admin=False)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("用户创建成功。", "success")
        return redirect(url_for("admin.users"))

    return render_template("admin/create_user.html")


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
def delete_user(user_id: int):
    user = User.query.get_or_404(user_id)

    # 不允许删除管理员账号（尤其是自己）
    if user.is_admin:
        flash("不能删除管理员账号。", "danger")
        return redirect(url_for("admin.users"))

    db.session.delete(user)
    db.session.commit()
    flash("用户及其设备已删除。", "success")
    return redirect(url_for("admin.users"))


# ---------- 管理员重置任意用户密码 ----------
@bp.route("/users/<int:user_id>/reset_password", methods=["GET", "POST"])
@login_required
def reset_password(user_id: int):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        new = request.form.get("new_password", "").strip()
        confirm = request.form.get("confirm_password", "").strip()

        if not new:
            flash("新密码不能为空。", "danger")
        elif new != confirm:
            flash("两次输入的新密码不一致。", "danger")
        else:
            user.set_password(new)
            db.session.commit()
            flash(f"用户 {user.username} 的密码已重置。", "success")
            return redirect(url_for("admin.users"))

    return render_template("admin/reset_password.html", user=user)


# ---------- 设备管理 ----------

@bp.route("/users/<int:user_id>/devices")
@login_required
def devices(user_id: int):
    user = User.query.get_or_404(user_id)
    return render_template("admin/devices.html", user=user, devices=user.devices)


@bp.route("/users/<int:user_id>/devices/create", methods=["GET", "POST"])
@login_required
def create_device(user_id: int):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("设备名称不能为空。", "danger")
            return redirect(url_for("admin.create_device", user_id=user_id))

        wg_ip = wireguard.allocate_ip()
        priv, pub = wireguard.generate_keys()

        device = Device(
            name=name,
            user_id=user.id,
            wg_ip=wg_ip,
            wg_private_key=priv,
            wg_public_key=pub,
        )
        db.session.add(device)
        db.session.commit()

        config_text = wireguard.build_client_config(device)

        # 生成后直接展示配置文本，方便复制 / 保存
        return render_template(
            "admin/device_config.html",
            user=user,
            device=device,
            config_text=config_text,
        )

    return render_template("admin/create_device.html", user=user)
