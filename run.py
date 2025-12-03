from app import create_app

app = create_app()

if __name__ == "__main__":
    # 开发阶段用 debug，部署时记得关掉
    app.run(host="0.0.0.0", port=8000, debug=True)
