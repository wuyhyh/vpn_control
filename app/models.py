from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    devices = db.relationship(
        "Device",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Device(db.Model):
    __tablename__ = "devices"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    wg_private_key = db.Column(db.String(128), nullable=False)
    wg_public_key = db.Column(db.String(128), nullable=False)
    wg_ip = db.Column(db.String(32), nullable=False)

    revoked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def init_db() -> None:
    """创建表，并确保系统内存在固定的管理员账号。

    当前设计为两个管理员：
    - admin    ：初始超级管理员，默认密码 admin（部署前务必修改）
    - wuyuhang ：第二个管理员，默认密码也在这里设置（建议改成你自己的）

    说明：
    - Web 后台“创建用户”接口只创建普通用户（is_admin=False）。
    - 如果以后确实需要增加新的管理员账号，建议：
      1）在本函数中仿照 ensure_admin(...) 再添加一行，或
      2）写一个单独的管理脚本/命令行，在 app_context 下创建 User(is_admin=True)。

    不建议在 Web 界面随意增加管理员，以避免权限失控。
    """
    db.create_all()

    def ensure_admin(username: str, password: str) -> None:
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, is_admin=True)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

    # 超级管理员 1：admin
    ensure_admin("admin", "admin")  # 部署前请登录后立刻修改密码

    # 超级管理员 2：wuyuhang
    ensure_admin("wuyuhang", "wuyh12#$")  # 这里写成你想要的初始密码
