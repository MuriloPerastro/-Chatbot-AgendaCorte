
from flask import Blueprint, jsonify, request
from ..database import supabase

agendamento_bp = Blueprint(
    "agendamento",
    __name__,
    url_prefix="/api/agendamento"
)


# LISTAR SERVIÇOS DISPONÍVEIS
@agendamento_bp.route("/servicos", methods=["GET"])
def listar_servicos():
    try:
        resultado = (
            supabase.table("servicos")
            .select("id, nome, preco, duracao_minutos")
            .order("nome")
            .execute()
        )

        return jsonify({
            "servicos": resultado.data
        }), 200

    except Exception as erro:
        print("Erro ao buscar serviços:", erro)

        return jsonify({
            "erro": "Não foi possível carregar os serviços."
        }), 500
