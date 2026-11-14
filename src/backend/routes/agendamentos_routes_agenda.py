
from datetime import date, datetime, time, timedelta

from flask import Blueprint, jsonify, request

from ..database import supabase


agenda_bp = Blueprint(
    "agenda",
    __name__,
    url_prefix="/api/agenda"
)


# CONFIGURAÇÕES DO EXPEDIENTE.
INTERVALO_MINUTOS = 30

PERIODOS_FUNCIONAMENTO = [
    (time(8, 0), time(12, 0)),
    (time(14, 0), time(18, 0))
]


# CONVERTER HORÁRIO DO BANCO PARA DATETIME.
def converter_datetime(valor):
    return datetime.fromisoformat(
        valor.replace("Z", "+00:00")
    ).replace(tzinfo=None)


# BUSCAR HORÁRIOS DISPONÍVEIS.
@agenda_bp.route("/horarios", methods=["GET"])
def listar_horarios():
    profissional_id = request.args.get("profissional_id")
    servico_id = request.args.get("servico_id")
    data_texto = request.args.get("data")

    # Validar os parâmetros.
    if not profissional_id or not servico_id or not data_texto:
        return jsonify({
            "erro": "Informe profissional, serviço e data."
        }), 400

    try:
        profissional_id = int(profissional_id)
        servico_id = int(servico_id)
        data_atendimento = date.fromisoformat(data_texto)

    except (ValueError, TypeError):
        return jsonify({
            "erro": "Os dados informados são inválidos."
        }), 400

    # Não permitir datas anteriores.
    if data_atendimento < date.today():
        return jsonify({
            "erro": "Não é possível agendar em uma data passada."
        }), 400

    # Não permitir sábados e domingos.
    if data_atendimento.weekday() >= 5:
        return jsonify({
            "mensagem": "O salão não realiza atendimentos aos finais de semana.",
            "horarios": []
        })

    try:
        # Confirmar que o profissional está ativo.
        profissional = (
            supabase.table("profissionais")
            .select("id")
            .eq("id", profissional_id)
            .eq("ativo", True)
            .limit(1)
            .execute()
        )

        if not profissional.data:
            return jsonify({
                "erro": "Profissional não encontrado."
            }), 404

        # Confirmar que o profissional atende esse serviço.
        vinculo = (
            supabase.table("profissional_servicos")
            .select("id")
            .eq("profissional_id", profissional_id)
            .eq("servico_id", servico_id)
            .limit(1)
            .execute()
        )

        if not vinculo.data:
            return jsonify({
                "erro": "Esse profissional não atende o serviço escolhido."
            }), 400

        # Buscar duração do serviço.
        servico = (
            supabase.table("servicos")
            .select("duracao_minutos")
            .eq("id", servico_id)
            .limit(1)
            .execute()
        )

        if not servico.data:
            return jsonify({
                "erro": "Serviço não encontrado."
            }), 404

        duracao = servico.data[0]["duracao_minutos"]

        if not duracao or duracao <= 0:
            return jsonify({
                "erro": "A duração do serviço não está configurada."
            }), 400

        # Buscar agendamentos do profissional naquela data.
        inicio_dia = datetime.combine(
            data_atendimento,
            time(0, 0)
        )

        fim_dia = inicio_dia + timedelta(days=1)

        resultado = (
            supabase.table("agendamentos")
            .select(
                "data_hora_inicio, data_hora_fim, status"
            )
            .eq("profissional_id", profissional_id)
            .gte(
                "data_hora_inicio",
                inicio_dia.isoformat()
            )
            .lt(
                "data_hora_inicio",
                fim_dia.isoformat()
            )
            .execute()
        )

        agendamentos = resultado.data or []

        horarios_disponiveis = []

        # Verificar cada período de funcionamento.
        for inicio_periodo, fim_periodo in PERIODOS_FUNCIONAMENTO:

            inicio = datetime.combine(
                data_atendimento,
                inicio_periodo
            )

            fim = datetime.combine(
                data_atendimento,
                fim_periodo
            )

            horario_atual = inicio

            while horario_atual + timedelta(
                minutes=duracao
            ) <= fim:

                horario_final = horario_atual + timedelta(
                    minutes=duracao
                )

                ocupado = False

                # Verificar sobreposição com outros agendamentos.
                for agendamento in agendamentos:

                    if agendamento["status"].strip().lower() in [
                        "cancelado",
                        "cancelada"
                    ]:
                        continue

                    inicio_existente = converter_datetime(
                        agendamento["data_hora_inicio"]
                    )

                    fim_existente = converter_datetime(
                        agendamento["data_hora_fim"]
                    )

                    if (
                        inicio_existente < horario_final
                        and fim_existente > horario_atual
                    ):
                        ocupado = True
                        break

                if not ocupado:
                    horarios_disponiveis.append({
                        "id": horario_atual.strftime("%H:%M"),
                        "texto": horario_atual.strftime("%H:%M"),
                        "inicio": horario_atual.isoformat(),
                        "fim": horario_final.isoformat()
                    })

                horario_atual += timedelta(
                    minutes=INTERVALO_MINUTOS
                )

        return jsonify({
            "data": data_atendimento.isoformat(),
            "profissional_id": profissional_id,
            "servico_id": servico_id,
            "duracao_minutos": duracao,
            "horarios": horarios_disponiveis
        })

    except Exception as erro:
        print("Erro ao consultar horários:", erro)

        return jsonify({
            "erro": "Não foi possível consultar os horários disponíveis."
        }), 500
