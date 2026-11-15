
from datetime import date, datetime, time, timedelta
import hmac
import os

from flask import Blueprint, jsonify, request, session

from ..database import supabase


# NOMES E IMAGENS DOS PROFISSIONAIS.
NOMES_PROFISSIONAIS = {
    1: {
        "nome": "Rodrigo",
        "imagem": "Rodrigo.png"
    },
    2: {
        "nome": "Cleber",
        "imagem": "Cleber.png"
    },
    3: {
        "nome": "Carina",
        "imagem": "Carina.png"
    }
}

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/api/admin"
)


# AUTENTICAÇÃO ADMINISTRATIVA.
def administrador_autenticado():
    return session.get("administrador") is True


@admin_bp.route("/login", methods=["POST"])
def login():
    dados = request.get_json(silent=True) or {}
    senha = dados.get("senha", "")

    senha_admin = os.getenv("ADMIN_PASSWORD")

    if not senha_admin:
        return jsonify({
            "erro": "A senha administrativa não está configurada no servidor."
        }), 500

    if not isinstance(senha, str) or not hmac.compare_digest(
        senha,
        senha_admin
    ):
        return jsonify({
            "erro": "Senha incorreta."
        }), 401

    session.clear()
    session["administrador"] = True
    session.permanent = True

    return jsonify({
        "mensagem": "Acesso administrativo autorizado."
    })


@admin_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()

    return jsonify({
        "mensagem": "Sessão administrativa encerrada."
    })


# CONSULTAR A AGENDA SEMANAL.
@admin_bp.route("/agenda", methods=["GET"])
def listar_agenda():
    if not administrador_autenticado():
        return jsonify({
            "erro": "Acesso não autorizado."
        }), 401

    try:
        # Recebe uma data opcional para navegar entre semanas.
        data_texto = request.args.get("inicio")

        if data_texto:
            data_referencia = date.fromisoformat(data_texto)
        else:
            data_referencia = date.today()

        # Ajusta para segunda-feira da semana escolhida.
        inicio_semana = data_referencia - timedelta(
            days=data_referencia.weekday()
        )

        fim_semana = inicio_semana + timedelta(days=7)

        inicio_datetime = datetime.combine(
            inicio_semana,
            time.min
        )

        fim_datetime = datetime.combine(
            fim_semana,
            time.min
        )

        # Busca os agendamentos da semana.
        resultado = (
            supabase.table("agendamentos")
            .select(
                "id, cliente_id, profissional_id, servico_id, "
                "tipo_cabelo, data_hora_inicio, data_hora_fim, status"
            )
            .gte(
                "data_hora_inicio",
                inicio_datetime.isoformat()
            )
            .lt(
                "data_hora_inicio",
                fim_datetime.isoformat()
            )
            .order("data_hora_inicio")
            .execute()
        )

        agendamentos = resultado.data or []

        # Busca os profissionais.
        resultado_profissionais = (
    supabase.table("profissionais")
    .select("id, ativo")
    .execute()
)

        profissionais = resultado_profissionais.data or []

        # Identifica os clientes e serviços utilizados.
        clientes_ids = list({
            item["cliente_id"]
            for item in agendamentos
            if item.get("cliente_id") is not None
        })

        servicos_ids = list({
            item["servico_id"]
            for item in agendamentos
            if item.get("servico_id") is not None
        })

        clientes = []
        servicos = []

        if clientes_ids:
            resultado_clientes = (
                supabase.table("clientes")
                .select("id, nome_completo")
                .in_("id", clientes_ids)
                .execute()
            )

            clientes = resultado_clientes.data or []

        if servicos_ids:
            resultado_servicos = (
                supabase.table("servicos")
                .select("id, nome")
                .in_("id", servicos_ids)
                .execute()
            )

            servicos = resultado_servicos.data or []

        # Cria índices para localizar os dados rapidamente.
        clientes_por_id = {
            item["id"]: item
            for item in clientes
        }

        servicos_por_id = {
            item["id"]: item
            for item in servicos
        }

        # Organiza os agendamentos por profissional.
        agenda_organizada = []

        for profissional in profissionais:
            agendamentos_profissional = []

            for agendamento in agendamentos:
                if (
                    agendamento["profissional_id"]
                    != profissional["id"]
                ):
                    continue

                cliente = clientes_por_id.get(
                    agendamento.get("cliente_id")
                )

                servico = servicos_por_id.get(
                    agendamento.get("servico_id")
                )

                inicio = datetime.fromisoformat(
                    agendamento["data_hora_inicio"].replace(
                        "Z",
                        "+00:00"
                    )
                )

                fim = datetime.fromisoformat(
                    agendamento["data_hora_fim"].replace(
                        "Z",
                        "+00:00"
                    )
                )

                agendamentos_profissional.append({
                    "id": agendamento["id"],
                    "cliente": (
                        cliente["nome_completo"]
                        if cliente else "Cliente não identificado"
                    ),
                    "servico": (
                        servico["nome"]
                        if servico else "Serviço não identificado"
                    ),
                    "tipo_cabelo": agendamento.get("tipo_cabelo"),
                    "data": inicio.date().isoformat(),
                    "dia_semana": inicio.weekday(),
                    "horario_inicio": inicio.strftime("%H:%M"),
                    "horario_fim": fim.strftime("%H:%M"),
                    "status": agendamento.get("status")
                })

            # Recupera o nome configurado para o profissional.
                dados_profissional = NOMES_PROFISSIONAIS.get(
                    profissional["id"],
                    {
                        "nome": f"Profissional {profissional['id']}",
                        "imagem": ""
                    }
                )

                agenda_organizada.append({
                    "profissional_id": profissional["id"],
                    "profissional": dados_profissional["nome"],
                    "imagem": dados_profissional["imagem"],
                    "ativo": profissional["ativo"],
                    "agendamentos": agendamentos_profissional
                })

        return jsonify({
            "inicio_semana": inicio_semana.isoformat(),
            "fim_semana": (fim_semana - timedelta(days=1)).isoformat(),
            "profissionais": agenda_organizada
        })

    except ValueError:
        return jsonify({
            "erro": "A data informada é inválida."
        }), 400

    except Exception as erro:
        print("Erro ao consultar agenda administrativa:", erro)

        return jsonify({
            "erro": "Não foi possível carregar a agenda administrativa."
        }), 500
    # EXCLUIR UM AGENDAMENTO.
@admin_bp.route(
    "/agendamento/<int:agendamento_id>",
    methods=["DELETE"]
)
def excluir_agendamento(agendamento_id):

    # Verifica a autenticação administrativa.
    if not administrador_autenticado():
        return jsonify({
            "erro": "Acesso não autorizado."
        }), 401

    try:
        # Confirma que o agendamento existe.
        resultado = (
            supabase.table("agendamentos")
            .select("id")
            .eq("id", agendamento_id)
            .limit(1)
            .execute()
        )

        if not resultado.data:
            return jsonify({
                "erro": "Agendamento não encontrado."
            }), 404

        # Exclui o agendamento.
        supabase.table("agendamentos") \
            .delete() \
            .eq("id", agendamento_id) \
            .execute()

        return jsonify({
            "mensagem": "Agendamento excluído com sucesso.",
            "id": agendamento_id
        })

    except Exception as erro:
        print("Erro ao excluir agendamento:", erro)

        return jsonify({
            "erro": "Não foi possível excluir o agendamento."
        }), 500
