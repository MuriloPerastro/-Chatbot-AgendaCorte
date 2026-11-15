import os
from datetime import timedelta

from .routes.admin_routes import admin_bp
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from .database import supabase
from .routes.chat_routes import chat_bp
from .routes.agendamento_routes import agendamento_bp
from .routes.agendamentos_routes_agenda import agenda_bp


# Caminho da raiz do projeto.
BASE_DIR = Path(__file__).resolve().parents[2]

# Pastas do frontend e das imagens.
FRONTEND_DIR = BASE_DIR / "public"
ASSETS_DIR = FRONTEND_DIR / "assets"


# Inicialização do Flask.
app = Flask(
    __name__,
    static_folder=str(FRONTEND_DIR),
    static_url_path=""
)
# Configuração de segurança das sessões administrativas.
app.secret_key = os.getenv("SECRET_KEY")

if not app.secret_key:
    raise ValueError("Configure SECRET_KEY nas variáveis de ambiente.")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("VERCEL") == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8)
)

# Registro das rotas.
app.register_blueprint(chat_bp)
app.register_blueprint(agendamento_bp)
app.register_blueprint(agenda_bp)
app.register_blueprint(admin_bp)


# Página inicial.
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


# Disponibiliza imagens.
@app.route("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(ASSETS_DIR, filename)


# Verifica se o servidor está funcionando.
@app.route("/api/status", methods=["GET"])
def status():
    return jsonify({
        "sistema": "AgendaCorte",
        "servidor": "online",
        "supabase": supabase is not None
    })


# Inicialização local.
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
