
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from .database import supabase
from .routes.chat_routes import chat_bp
from .routes.agendamento_routes import agendamento_bp
from .routes.agendamentos_routes_agenda import agenda_bp


# Caminho da pasta src.
BASE_DIR = Path(__file__).resolve().parent.parent

# Pastas do projeto.
FRONTEND_DIR = BASE_DIR / "frontend"
ASSETS_DIR = BASE_DIR / "assets"


# Inicialização do Flask.
app = Flask(
    __name__,
    static_folder=str(FRONTEND_DIR),
    static_url_path=""
)


# Registro das rotas.
app.register_blueprint(chat_bp)
app.register_blueprint(agendamento_bp)
app.register_blueprint(agenda_bp)


# Página inicial.
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


# Disponibiliza imagens.
@app.route("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(ASSETS_DIR, filename)


# Verificação do servidor.
@app.route("/api/status", methods=["GET"])
def status():
    return jsonify({
        "sistema": "AgendaCorte",
        "servidor": "online",
        "supabase": supabase is not None
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
