from flask import Flask
from .config import Config
from .models import db, init_db
from .views_auth import bp as auth_bp
from .views_admin import bp as admin_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    # WireGuard 公钥缺失直接报错，提醒先初始化
    if not app.config["WG_SERVER_PUBLIC_KEY"]:
        raise RuntimeError(
            "WG_SERVER_PUBLIC_KEY 为空。请先在 Rocky 上运行 "
            "scripts/wg_init_server.sh 生成 /etc/wireguard/server.key.pub。"
        )

    db.init_app(app)

    # 初始化数据库 & 默认 admin 用户
    with app.app_context():
        init_db()

    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    return app
