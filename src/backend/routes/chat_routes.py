
import re
import unicodedata

from datetime import date, datetime, time, timedelta

from flask import Blueprint, jsonify, request

from ..database import supabase


chat_bp = Blueprint(
    "chat",
    __name__,
    url_prefix="/api/chat"
)


# =========================================================
# 1. CONFIGURAÇÕES GERAIS
# =========================================================

# Intervalo entre os horários oferecidos pelo chatbot.
INTERVALO_MINUTOS = 30

# Expediente do salão: manhã e tarde.
PERIODOS_FUNCIONAMENTO = [
    (time(8, 0), time(12, 0)),
    (time(14, 0), time(18, 0))
]

# Nomes e imagens exibidos no frontend.
# Os IDs correspondem aos registros da tabela profissionais.
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

# Opções de tipo de cabelo.
TIPOS_CABELO = {
    "cabelo_natural": "Natural",
    "cabelo_descolorido": "Com descoloração",
    "cabelo_tingido": "Com tintura",
    "cabelo_outro": "Outros"
}

# Status que não ocupam horários.
STATUS_CANCELADOS = {
    "cancelado",
    "cancelada"
}


# =========================================================
# 2. FUNÇÕES AUXILIARES
# =========================================================

def normalizar_comando(texto):
    """
    Padroniza o texto digitado pelo usuário.

    Remove espaços extras, converte para minúsculas
    e remove acentos.
    """

    texto = texto.strip().lower()

    texto = unicodedata.normalize("NFD", texto)

    texto = "".join(
        caractere
        for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )

    return texto


def resposta(mensagem, etapa, opcoes=None, status=200, **dados):
    """
    Padroniza todas as respostas enviadas ao JavaScript.

    Cada resposta contém:
    - mensagem: texto exibido pelo chatbot.
    - etapa: etapa atual do atendimento.
    - opcoes: botões exibidos.
    - dados adicionais: IDs e informações do atendimento.
    """

    resultado = {
        "mensagem": mensagem,
        "etapa": etapa,
        "opcoes": opcoes or []
    }

    resultado.update(dados)

    return jsonify(resultado), status


def obter_id_inteiro(valor):
    """
    Converte um ID recebido do frontend em inteiro.
    Impede IDs inválidos ou menores que 1.
    """

    try:
        identificador = int(valor)

        if identificador <= 0:
            return None

        return identificador

    except (ValueError, TypeError):
        return None


def validar_telefone(texto):
    """
    Valida telefone brasileiro com DDD.

    Aceita 10 ou 11 números, com ou sem formatação.
    """

    if not isinstance(texto, str):
        return None

    if not re.fullmatch(r"[0-9\s()+.-]+", texto):
        return None

    telefone = "".join(
        caractere
        for caractere in texto
        if caractere.isdigit()
    )

    if len(telefone) not in (10, 11):
        return None

    return telefone


def validar_nome(nome):
    """
    Exige nome completo, com pelo menos duas partes.
    Aceita letras, acentos, espaços, apóstrofos e hífens.
    """

    if not isinstance(nome, str):
        return False

    nome = nome.strip()

    padrao = r"^[^\W\d_]+(?:[ '-][^\W\d_]+)+$"

    return (
        len(nome) >= 3
        and re.fullmatch(padrao, nome) is not None
    )


def validar_data_nascimento(texto):
    """
    Valida uma data no formato DD/MM/AAAA.
    Também aceita a entrada numérica DDMMYYYY.
    """

    if not isinstance(texto, str):
        return None

    texto = texto.strip()

    if re.fullmatch(r"\d{8}", texto):
        texto = (
            f"{texto[:2]}/"
            f"{texto[2:4]}/"
            f"{texto[4:]}"
        )

    if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", texto):
        return None

    try:
        data_validada = datetime.strptime(
            texto,
            "%d/%m/%Y"
        ).date()

        if data_validada > date.today():
            return None

        return {
            "formatada": data_validada.strftime("%d/%m/%Y"),
            "banco": data_validada.isoformat()
        }

    except ValueError:
        return None


def converter_datetime(valor):
    """
    Converte valores de data e hora retornados pelo Supabase.

    O banco deste projeto utiliza timestamp sem fuso horário.
    """

    if isinstance(valor, datetime):
        return valor.replace(tzinfo=None)

    if not isinstance(valor, str):
        raise ValueError("Data e hora inválidas.")

    return datetime.fromisoformat(
        valor.replace("Z", "+00:00")
    ).replace(tzinfo=None)


# =========================================================
# 3. ACESSO AOS DADOS DO SUPABASE
# =========================================================

def buscar_cliente(cliente_id):
    """Busca um cliente pelo ID."""

    cliente_id = obter_id_inteiro(cliente_id)

    if not cliente_id:
        return None

    resultado = (
        supabase.table("clientes")
        .select("id, nome_completo, celular")
        .eq("id", cliente_id)
        .limit(1)
        .execute()
    )

    if not resultado.data:
        return None

    return resultado.data[0]


def buscar_cliente_por_telefone(telefone):
    """Busca um cliente pelo telefone."""

    resultado = (
        supabase.table("clientes")
        .select("id, nome_completo, celular")
        .eq("celular", telefone)
        .limit(1)
        .execute()
    )

    if not resultado.data:
        return None

    return resultado.data[0]


def buscar_servico(servico_id):
    """Busca um serviço e seus dados."""

    servico_id = obter_id_inteiro(servico_id)

    if not servico_id:
        return None

    resultado = (
        supabase.table("servicos")
        .select("id, nome, preco, duracao_minutos")
        .eq("id", servico_id)
        .limit(1)
        .execute()
    )

    if not resultado.data:
        return None

    return resultado.data[0]


def buscar_profissional(profissional_id, servico_id=None):
    """
    Busca um profissional ativo.

    Quando recebe um serviço, também verifica se existe
    vínculo entre o profissional e aquele serviço.
    """

    profissional_id = obter_id_inteiro(profissional_id)

    if not profissional_id:
        return None

    resultado = (
        supabase.table("profissionais")
        .select("id, ativo")
        .eq("id", profissional_id)
        .eq("ativo", True)
        .limit(1)
        .execute()
    )

    if not resultado.data:
        return None

    if servico_id is not None:
        servico_id = obter_id_inteiro(servico_id)

        if not servico_id:
            return None

        vinculo = (
            supabase.table("profissional_servicos")
            .select("id")
            .eq("profissional_id", profissional_id)
            .eq("servico_id", servico_id)
            .limit(1)
            .execute()
        )

        if not vinculo.data:
            return None

    return resultado.data[0]


def listar_opcoes_servicos():
    """
    Busca os serviços no banco e monta os botões
    com nome, preço e duração.
    """

    resultado = (
        supabase.table("servicos")
        .select("id, nome, preco, duracao_minutos")
        .order("nome")
        .execute()
    )

    opcoes = []

    for servico in resultado.data or []:
        preco = float(servico["preco"])

        preco_formatado = (
            f"R$ {preco:.2f}".replace(".", ",")
        )

        duracao = servico.get("duracao_minutos") or 30

        opcoes.append({
            "id": f"servico_{servico['id']}",
            "texto": (
                f"{servico['nome']} — "
                f"{preco_formatado} "
                f"({duracao} minutos)"
            )
        })

    return opcoes


def buscar_profissionais(servico_id):
    """
    Busca os profissionais vinculados ao serviço escolhido.
    Retorna os nomes e imagens usados nos cartões do frontend.
    """

    servico_id = obter_id_inteiro(servico_id)

    if not servico_id:
        return []

    vinculos = (
        supabase.table("profissional_servicos")
        .select("profissional_id")
        .eq("servico_id", servico_id)
        .execute()
    )

    ids_profissionais = sorted({
        item["profissional_id"]
        for item in (vinculos.data or [])
        if item.get("profissional_id") is not None
    })

    if not ids_profissionais:
        return []

    resultado = (
        supabase.table("profissionais")
        .select("id, ativo")
        .in_("id", ids_profissionais)
        .eq("ativo", True)
        .execute()
    )

    profissionais = []

    for profissional in resultado.data or []:
        identificacao = NOMES_PROFISSIONAIS.get(
            profissional["id"]
        )

        if not identificacao:
            continue

        profissionais.append({
            "id": f"profissional_{profissional['id']}",
            "texto": identificacao["nome"],
            "imagem": identificacao["imagem"]
        })

    return profissionais


# =========================================================
# 4. DATAS DISPONÍVEIS
# =========================================================

def gerar_datas_disponiveis(quantidade=10):
    """
    Gera os próximos dias úteis.

    Não considera feriados, pois essa informação ainda
    não está configurada no projeto.
    """

    datas = []

    dia = date.today()

    while len(datas) < quantidade:
        if dia.weekday() < 5:
            datas.append({
                "id": f"data_{dia.isoformat()}",
                "texto": dia.strftime("%d/%m/%Y")
            })

        dia += timedelta(days=1)

    return datas


# =========================================================
# 5. CONSULTA DE HORÁRIOS DISPONÍVEIS
# =========================================================

def consultar_horarios_disponiveis(
    profissional_id,
    servico_id,
    data_atendimento
):
    """
    Calcula os horários livres de um profissional.

    Considera:
    - Profissional ativo.
    - Vínculo entre profissional e serviço.
    - Duração do serviço.
    - Expediente e intervalo de almoço.
    - Agendamentos existentes.
    - Horários que já passaram.
    """

    profissional_id = obter_id_inteiro(profissional_id)
    servico_id = obter_id_inteiro(servico_id)

    profissional = buscar_profissional(
        profissional_id,
        servico_id
    )

    if not profissional:
        raise ValueError(
            "O profissional não está disponível para esse serviço."
        )

    servico = buscar_servico(servico_id)

    if not servico:
        raise ValueError("Serviço não encontrado.")

    duracao = servico.get("duracao_minutos")

    if (
        not isinstance(duracao, int)
        or duracao <= 0
    ):
        raise ValueError(
            "A duração do serviço não está configurada corretamente."
        )

    if data_atendimento < date.today():
        raise ValueError(
            "Não é possível agendar em uma data passada."
        )

    if data_atendimento.weekday() >= 5:
        return []

    inicio_dia = datetime.combine(
        data_atendimento,
        time(0, 0)
    )

    fim_dia = inicio_dia + timedelta(days=1)

    # Busca os agendamentos do profissional naquela data.
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

    horarios = []
    agora = datetime.now()

    # Percorre os períodos de funcionamento.
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

        # O serviço precisa terminar dentro do expediente.
        while (
            horario_atual + timedelta(minutes=duracao)
            <= fim
        ):
            horario_final = horario_atual + timedelta(
                minutes=duracao
            )

            # Não oferece horários que já passaram.
            if (
                data_atendimento == date.today()
                and horario_atual <= agora
            ):
                horario_atual += timedelta(
                    minutes=INTERVALO_MINUTOS
                )
                continue

            ocupado = False

            # Verifica se existe sobreposição.
            for agendamento in agendamentos:

                status = (
                    agendamento.get("status") or ""
                ).strip().lower()

                if status in STATUS_CANCELADOS:
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
                horarios.append({
                    "id": (
                        f"horario_"
                        f"{horario_atual.strftime('%H:%M')}"
                    ),
                    "texto": horario_atual.strftime("%H:%M")
                })

            horario_atual += timedelta(
                minutes=INTERVALO_MINUTOS
            )

    return horarios


# =========================================================
# 6. CONSULTAR AGENDAMENTOS DO CLIENTE
# =========================================================

def consultar_agendamentos_cliente(cliente_id):
    """
    Busca os próximos agendamentos de um cliente.

    Os nomes dos profissionais são obtidos pelo mapeamento
    local e os nomes dos serviços são buscados no Supabase.
    """

    cliente_id = obter_id_inteiro(cliente_id)

    if not cliente_id:
        raise ValueError("Cliente inválido.")

    agora = datetime.now()

    resultado = (
        supabase.table("agendamentos")
        .select(
            "id, profissional_id, servico_id, "
            "data_hora_inicio, data_hora_fim, status"
        )
        .eq("cliente_id", cliente_id)
        .gte(
            "data_hora_inicio",
            agora.isoformat()
        )
        .order("data_hora_inicio")
        .limit(10)
        .execute()
    )

    agendamentos = resultado.data or []

    # Remove registros cancelados.
    agendamentos = [
        item
        for item in agendamentos
        if (
            item.get("status") or ""
        ).strip().lower() not in STATUS_CANCELADOS
    ]

    if not agendamentos:
        return []

    opcoes = []

    for agendamento in agendamentos:
        servico = buscar_servico(
            agendamento["servico_id"]
        )

        profissional = NOMES_PROFISSIONAIS.get(
            agendamento["profissional_id"],
            {"nome": "Profissional"}
        )

        inicio = converter_datetime(
            agendamento["data_hora_inicio"]
        )

        fim = converter_datetime(
            agendamento["data_hora_fim"]
        )

        nome_servico = (
            servico["nome"]
            if servico
            else "Serviço"
        )

        opcoes.append({
            "id": f"agendamento_{agendamento['id']}",
            "texto": (
                f"{nome_servico} — "
                f"{profissional['nome']} — "
                f"{inicio.strftime('%d/%m/%Y')} "
                f"às {inicio.strftime('%H:%M')} "
                f"(até {fim.strftime('%H:%M')})"
            )
        })

    return opcoes

def buscar_agendamento_cliente(agendamento_id, cliente_id):
    """
    Busca um agendamento específico pertencente ao cliente.

    A consulta utiliza os dois IDs para impedir que a operação
    seja realizada sobre o agendamento de outro cadastro.
    """

    agendamento_id = obter_id_inteiro(agendamento_id)
    cliente_id = obter_id_inteiro(cliente_id)

    if not agendamento_id or not cliente_id:
        return None

    resultado = (
        supabase.table("agendamentos")
        .select(
            "id, cliente_id, profissional_id, servico_id, "
            "data_hora_inicio, data_hora_fim, status"
        )
        .eq("id", agendamento_id)
        .eq("cliente_id", cliente_id)
        .limit(1)
        .execute()
    )

    if not resultado.data:
        return None

    return resultado.data[0]


# =========================================================
# 7. INICIAR CONVERSA
# =========================================================

@chat_bp.route("/iniciar", methods=["GET"])
def iniciar_conversa():
    """
    Primeira mensagem exibida quando a página é carregada.
    """

    return resposta(
        "Olá! Tudo bem? Como posso te ajudar?",
        "inicio",
        [
            {
                "id": "agendar",
                "texto": "Agendar"
            },
            {
                "id": "ver_agendamentos",
                "texto": "Ver meus agendamentos"
            }
        ]
    )


# =========================================================
# 8. PROCESSAR OPÇÕES DOS BOTÕES
# =========================================================

@chat_bp.route("/responder", methods=["POST"])
def responder():
    """
    Processa as opções clicadas pelo usuário.

    O frontend deve enviar:
    - opcao
    - cliente_id
    - servico_id
    - profissional_id
    - tipo_cabelo
    - data_agendamento
    """

    dados = request.get_json(silent=True) or {}

    opcao = dados.get("opcao")

    # Aceita texto como alternativa, mas o frontend
    # deverá enviar o campo opcao corretamente.
    if not opcao:
        opcao = dados.get("texto")

    if not isinstance(opcao, str) or not opcao.strip():
        return resposta(
            "Nenhuma opção foi enviada.",
            dados.get("etapa") or "inicio",
            status=400
        )

    opcao = opcao.strip()

    cliente_id = obter_id_inteiro(
        dados.get("cliente_id")
    )

    servico_id = obter_id_inteiro(
        dados.get("servico_id")
    )

    profissional_id = obter_id_inteiro(
        dados.get("profissional_id")
    )

    tipo_cabelo = dados.get("tipo_cabelo")
    data_agendamento = dados.get("data_agendamento")

    # -----------------------------------------------------
    # AGENDAR OU CONSULTAR AGENDAMENTOS
    # -----------------------------------------------------

    if opcao in ("agendar", "ver_agendamentos"):

        try:
            cliente = buscar_cliente(cliente_id)

            if not cliente:
                return resposta(
                    "Antes de continuar, preciso identificar você. "
                    "Você já possui cadastro?",
                    "identificacao",
                    [
                        {
                            "id": "login",
                            "texto": "Já tenho cadastro"
                        },
                        {
                            "id": "cadastro",
                            "texto": "Quero me cadastrar"
                        }
                    ],
                    cliente_id=None
                )

            if opcao == "agendar":

                opcoes = listar_opcoes_servicos()

                if not opcoes:
                    return resposta(
                        "No momento, não temos serviços disponíveis.",
                        "agendamento_servico",
                        cliente_id=cliente["id"]
                    )

                return resposta(
                    (
                        f"Certo, {cliente['nome_completo']}! "
                        "Escolha o serviço desejado:"
                    ),
                    "agendamento_servico",
                    opcoes,
                    cliente_id=cliente["id"]
                )

            opcoes = consultar_agendamentos_cliente(
                cliente["id"]
            )

            if not opcoes:
                return resposta(
                    (
                        "Você não possui agendamentos futuros "
                        "confirmados no momento."
                    ),
                    "consultar_agendamentos",
                    [
                        {
                            "id": "agendar",
                            "texto": "Fazer um agendamento"
                        },
                        {
                            "id": "trocar_usuario",
                            "texto": "Atender outra pessoa"
                        }
                    ],
                    cliente_id=cliente["id"]
                )

            return resposta(
                (
                    f"Olá, {cliente['nome_completo']}! "
                    "Estes são seus próximos agendamentos:"
                ),
                "consultar_agendamentos",
                opcoes + [
                    {
                        "id": "agendar",
                        "texto": "Fazer outro agendamento"
                    },
                    {
                        "id": "trocar_usuario",
                        "texto": "Atender outra pessoa"
                    }
                ],
                cliente_id=cliente["id"]
            )

        except Exception as erro:
            print("Erro ao consultar cliente/agendamentos:", erro)

            return resposta(
                "Não foi possível consultar seus dados. Tente novamente.",
                "inicio",
                status=500
            )

    # -----------------------------------------------------
    # SELECIONAR AGENDAMENTO PARA CANCELAR
    # -----------------------------------------------------

    if opcao.startswith("agendamento_"):

        try:
            agendamento_id = obter_id_inteiro(
                opcao.removeprefix("agendamento_")
            )

            if not cliente_id:
                return resposta(
                    "Identifique sua conta antes de continuar.",
                    "identificacao",
                    [
                        {
                            "id": "login",
                            "texto": "Já tenho cadastro"
                        },
                        {
                            "id": "cadastro",
                            "texto": "Fazer cadastro"
                        }
                    ]
                )

            agendamento = buscar_agendamento_cliente(
                agendamento_id,
                cliente_id
            )

            if not agendamento:
                return resposta(
                    "Não encontrei esse agendamento na sua conta.",
                    "consultar_agendamentos",
                    consultar_agendamentos_cliente(cliente_id)
                )

            status = (
                agendamento.get("status") or ""
            ).strip().lower()

            if status in STATUS_CANCELADOS:
                return resposta(
                    "Esse agendamento já foi cancelado.",
                    "consultar_agendamentos",
                    consultar_agendamentos_cliente(cliente_id)
                )

            inicio = converter_datetime(
                agendamento["data_hora_inicio"]
            )

            fim = converter_datetime(
                agendamento["data_hora_fim"]
            )

            if inicio <= datetime.now():
                return resposta(
                    "Não é possível cancelar um atendimento que já começou ou passou.",
                    "consultar_agendamentos",
                    consultar_agendamentos_cliente(cliente_id)
                )

            servico = buscar_servico(
                agendamento["servico_id"]
            )

            profissional = NOMES_PROFISSIONAIS.get(
                agendamento["profissional_id"],
                {"nome": "Profissional"}
            )

            nome_servico = (
                servico["nome"]
                if servico
                else "Serviço"
            )

            return resposta(
                (
                    "Você selecionou este agendamento:\n\n"
                    f"Serviço: {nome_servico}\n"
                    f"Profissional: {profissional['nome']}\n"
                    f"Data: {inicio.strftime('%d/%m/%Y')}\n"
                    f"Horário: {inicio.strftime('%H:%M')} "
                    f"às {fim.strftime('%H:%M')}\n\n"
                    "Deseja realmente cancelar esse agendamento?"
                ),
                "cancelar_agendamento_confirmacao",
                [
                    {
                        "id": f"confirmar_cancelamento_{agendamento['id']}",
                        "texto": "Sim, cancelar agendamento"
                    },
                    {
                        "id": "voltar_agendamentos",
                        "texto": "Não, voltar"
                    }
                ],
                cliente_id=cliente_id
            )

        except Exception as erro:
            print("Erro ao selecionar agendamento:", erro)

            return resposta(
                "Não foi possível consultar esse agendamento. Tente novamente.",
                "consultar_agendamentos",
                status=500
            )

    # -----------------------------------------------------
    # VOLTAR PARA A LISTA DE AGENDAMENTOS
    # -----------------------------------------------------

    if opcao == "voltar_agendamentos":

        try:
            if not buscar_cliente(cliente_id):
                return resposta(
                    "Identifique sua conta novamente.",
                    "identificacao",
                    [
                        {
                            "id": "login",
                            "texto": "Já tenho cadastro"
                        },
                        {
                            "id": "cadastro",
                            "texto": "Fazer cadastro"
                        }
                    ],
                    cliente_id=None
                )

            opcoes = consultar_agendamentos_cliente(
                cliente_id
            )

            return resposta(
                "Aqui estão novamente seus agendamentos:",
                "consultar_agendamentos",
                opcoes + [
                    {
                        "id": "agendar",
                        "texto": "Fazer outro agendamento"
                    }
                ],
                cliente_id=cliente_id
            )

        except Exception as erro:
            print("Erro ao voltar para agendamentos:", erro)

            return resposta(
                "Não foi possível carregar seus agendamentos.",
                "consultar_agendamentos",
                status=500
            )

    # -----------------------------------------------------
    # CONFIRMAR CANCELAMENTO
    # -----------------------------------------------------

    if opcao.startswith("confirmar_cancelamento_"):

        try:
            agendamento_id = obter_id_inteiro(
                opcao.removeprefix("confirmar_cancelamento_")
            )

            if not cliente_id or not buscar_cliente(cliente_id):
                return resposta(
                    "Sua identificação expirou. Entre novamente na sua conta.",
                    "identificacao",
                    [
                        {
                            "id": "login",
                            "texto": "Já tenho cadastro"
                        },
                        {
                            "id": "cadastro",
                            "texto": "Fazer cadastro"
                        }
                    ],
                    cliente_id=None
                )

            # Confere novamente se o agendamento pertence ao cliente.
            agendamento = buscar_agendamento_cliente(
                agendamento_id,
                cliente_id
            )

            if not agendamento:
                return resposta(
                    "Não encontrei esse agendamento na sua conta.",
                    "consultar_agendamentos",
                    consultar_agendamentos_cliente(cliente_id)
                )

            status = (
                agendamento.get("status") or ""
            ).strip().lower()

            if status in STATUS_CANCELADOS:
                return resposta(
                    "Esse agendamento já foi cancelado.",
                    "consultar_agendamentos",
                    consultar_agendamentos_cliente(cliente_id)
                )

            inicio = converter_datetime(
                agendamento["data_hora_inicio"]
            )

            if inicio <= datetime.now():
                return resposta(
                    "Não é possível cancelar um atendimento que já começou ou passou.",
                    "consultar_agendamentos",
                    consultar_agendamentos_cliente(cliente_id)
                )

            # Exclui somente o registro pertencente ao cliente.
            (
                supabase.table("agendamentos")
                .delete()
                .eq("id", agendamento_id)
                .eq("cliente_id", cliente_id)
                .execute()
            )

            # Confirma que o registro realmente foi removido.
            verificacao = buscar_agendamento_cliente(
                agendamento_id,
                cliente_id
            )

            if verificacao:
                raise RuntimeError(
                    "O agendamento ainda existe no banco."
                )

            # Atualiza a lista após o cancelamento.
            opcoes = consultar_agendamentos_cliente(
                cliente_id
            )

            if opcoes:
                opcoes.append({
                    "id": "agendar",
                    "texto": "Fazer outro agendamento"
                })

                mensagem = (
                    "Agendamento cancelado com sucesso! "
                    "O horário foi liberado na agenda.\n\n"
                    "Estes são seus outros agendamentos:"
                )

            else:
                opcoes = [
                    {
                        "id": "agendar",
                        "texto": "Fazer um novo agendamento"
                    },
                    {
                        "id": "ver_agendamentos",
                        "texto": "Consultar agendamentos"
                    }
                ]

                mensagem = (
                    "Agendamento cancelado com sucesso! "
                    "O horário foi liberado na agenda.\n\n"
                    "Você não possui outros agendamentos futuros."
                )

            return resposta(
                mensagem,
                "consultar_agendamentos",
                opcoes,
                cliente_id=cliente_id
            )

        except Exception as erro:
            print("Erro ao cancelar agendamento:", erro)

            return resposta(
                (
                    "Não foi possível cancelar o agendamento. "
                    "Tente novamente."
                ),
                "consultar_agendamentos",
                status=500
            )

    # -----------------------------------------------------
    # TROCAR DE USUÁRIO
    # -----------------------------------------------------

    if opcao == "trocar_usuario":
        return resposta(
            "Quem vai utilizar o AgendaCorte agora?",
            "identificacao",
            [
                {
                    "id": "login",
                    "texto": "Já tenho cadastro"
                },
                {
                    "id": "cadastro",
                    "texto": "Fazer cadastro"
                }
            ],
            cliente_id=None,
            nome=None,
            servico_id=None,
            profissional_id=None,
            tipo_cabelo=None,
            data_agendamento=None
        )

    # -----------------------------------------------------
    # LOGIN
    # -----------------------------------------------------

    if opcao == "login":
        return resposta(
            "Informe seu telefone com DDD.",
            "login_telefone",
            cliente_id=None
        )

    # -----------------------------------------------------
    # CADASTRO
    # -----------------------------------------------------

    if opcao == "cadastro":
        return resposta(
            "Informe seu nome completo.",
            "cadastro_nome",
            cliente_id=None,
            nome=None,
            data_nascimento=None
        )

    # -----------------------------------------------------
    # SELEÇÃO DO SERVIÇO
    # -----------------------------------------------------

    if opcao.startswith("servico_"):

        try:
            identificador = opcao.removeprefix("servico_")

            novo_servico_id = obter_id_inteiro(
                identificador
            )

            if not novo_servico_id:
                return resposta(
                    "Serviço inválido.",
                    "agendamento_servico",
                    listar_opcoes_servicos(),
                    status=400
                )

            servico = buscar_servico(novo_servico_id)

            if not servico:
                return resposta(
                    "Esse serviço não foi encontrado.",
                    "agendamento_servico",
                    listar_opcoes_servicos(),
                    status=404
                )

            nome_servico = servico["nome"].strip().lower()

            # Corte exige a identificação do tipo de cabelo.
            if nome_servico == "corte":
                return resposta(
                    (
                        "Certo! Antes de continuar, "
                        "qual é o tipo atual do seu cabelo?"
                    ),
                    "agendamento_tipo_cabelo",
                    [
                        {
                            "id": chave,
                            "texto": valor
                        }
                        for chave, valor in TIPOS_CABELO.items()
                    ],
                    cliente_id=cliente_id,
                    servico_id=servico["id"],
                    profissional_id=None,
                    tipo_cabelo=None,
                    data_agendamento=None
                )

            # Outros serviços seguem diretamente para profissional.
            opcoes_profissionais = buscar_profissionais(
                servico["id"]
            )

            if not opcoes_profissionais:
                return resposta(
                    "Não encontramos profissionais para esse serviço.",
                    "agendamento_profissional",
                    cliente_id=cliente_id,
                    servico_id=servico["id"]
                )

            return resposta(
                (
                    f"Você escolheu {servico['nome']}. "
                    "Agora escolha o profissional:"
                ),
                "agendamento_profissional",
                opcoes_profissionais,
                cliente_id=cliente_id,
                servico_id=servico["id"],
                profissional_id=None,
                tipo_cabelo=None,
                data_agendamento=None
            )

        except Exception as erro:
            print("Erro ao selecionar serviço:", erro)

            return resposta(
                "Não foi possível selecionar esse serviço.",
                "agendamento_servico",
                status=500
            )

    # -----------------------------------------------------
    # SELEÇÃO DO TIPO DE CABELO
    # -----------------------------------------------------

    if opcao in TIPOS_CABELO:

        try:
            if not servico_id:
                return resposta(
                    "Não consegui identificar o serviço. Comece novamente.",
                    "inicio",
                    status=400
                )

            servico = buscar_servico(servico_id)

            if (
                not servico
                or servico["nome"].strip().lower() != "corte"
            ):
                return resposta(
                    "Essa opção não se aplica ao serviço escolhido.",
                    "agendamento_servico",
                    listar_opcoes_servicos(),
                    status=400
                )

            tipo_cabelo = TIPOS_CABELO[opcao]

            opcoes_profissionais = buscar_profissionais(
                servico_id
            )

            if not opcoes_profissionais:
                return resposta(
                    "Não encontramos profissionais para esse serviço.",
                    "agendamento_profissional",
                    cliente_id=cliente_id,
                    servico_id=servico_id,
                    tipo_cabelo=tipo_cabelo
                )

            return resposta(
                (
                    f"Tipo de cabelo: {tipo_cabelo}. "
                    "Agora escolha o profissional:"
                ),
                "agendamento_profissional",
                opcoes_profissionais,
                cliente_id=cliente_id,
                servico_id=servico_id,
                profissional_id=None,
                tipo_cabelo=tipo_cabelo,
                data_agendamento=None
            )

        except Exception as erro:
            print("Erro ao selecionar tipo de cabelo:", erro)

            return resposta(
                "Não foi possível registrar essa informação.",
                "agendamento_tipo_cabelo",
                status=500
            )

    # -----------------------------------------------------
    # SELEÇÃO DO PROFISSIONAL
    # -----------------------------------------------------

    if opcao.startswith("profissional_"):

        try:
            identificador = opcao.removeprefix(
                "profissional_"
            )

            novo_profissional_id = obter_id_inteiro(
                identificador
            )

            if not novo_profissional_id or not servico_id:
                return resposta(
                    "Não foi possível identificar o profissional ou serviço.",
                    "agendamento_profissional",
                    status=400
                )

            profissional = buscar_profissional(
                novo_profissional_id,
                servico_id
            )

            if not profissional:
                return resposta(
                    "Esse profissional não está disponível para o serviço.",
                    "agendamento_profissional",
                    buscar_profissionais(servico_id),
                    status=400
                )

            identificacao = NOMES_PROFISSIONAIS.get(
                novo_profissional_id
            )

            nome_profissional = (
                identificacao["nome"]
                if identificacao
                else "Profissional"
            )

            return resposta(
                (
                    f"Você escolheu {nome_profissional}! "
                    "Agora escolha a data do atendimento:"
                ),
                "agendamento_data",
                gerar_datas_disponiveis(),
                cliente_id=cliente_id,
                servico_id=servico_id,
                profissional_id=novo_profissional_id,
                tipo_cabelo=tipo_cabelo,
                data_agendamento=None
            )

        except Exception as erro:
            print("Erro ao selecionar profissional:", erro)

            return resposta(
                "Não foi possível selecionar esse profissional.",
                "agendamento_profissional",
                status=500
            )

    # -----------------------------------------------------
    # SELEÇÃO DA DATA
    # -----------------------------------------------------

    if opcao.startswith("data_"):

        try:
            data_texto = opcao.removeprefix("data_")

            data_escolhida = date.fromisoformat(
                data_texto
            )

            if not servico_id or not profissional_id:
                return resposta(
                    "Não consegui recuperar o serviço ou profissional escolhido.",
                    "inicio",
                    status=400
                )

            if data_escolhida < date.today():
                return resposta(
                    "Não é possível escolher uma data passada.",
                    "agendamento_data",
                    gerar_datas_disponiveis(),
                    status=400
                )

            if data_escolhida.weekday() >= 5:
                return resposta(
                    "O salão não realiza atendimentos aos finais de semana.",
                    "agendamento_data",
                    gerar_datas_disponiveis(),
                    status=400
                )

            horarios = consultar_horarios_disponiveis(
                profissional_id,
                servico_id,
                data_escolhida
            )

            if not horarios:
                return resposta(
                    (
                        "Não há horários disponíveis nessa data. "
                        "Escolha outro dia:"
                    ),
                    "agendamento_data",
                    gerar_datas_disponiveis(),
                    cliente_id=cliente_id,
                    servico_id=servico_id,
                    profissional_id=profissional_id,
                    tipo_cabelo=tipo_cabelo,
                    data_agendamento=None
                )

            return resposta(
                (
                    f"Data escolhida: "
                    f"{data_escolhida.strftime('%d/%m/%Y')}. "
                    "Agora escolha um horário disponível:"
                ),
                "agendamento_horario",
                horarios,
                cliente_id=cliente_id,
                servico_id=servico_id,
                profissional_id=profissional_id,
                tipo_cabelo=tipo_cabelo,
                data_agendamento=data_escolhida.isoformat()
            )

        except ValueError as erro:
            return resposta(
                str(erro),
                "agendamento_data",
                gerar_datas_disponiveis(),
                status=400
            )

        except Exception as erro:
            print("Erro ao consultar horários:", erro)

            return resposta(
                "Não foi possível consultar os horários. Tente novamente.",
                "agendamento_data",
                gerar_datas_disponiveis(),
                status=500
            )

    # -----------------------------------------------------
    # SELEÇÃO DO HORÁRIO E SALVAMENTO
    # -----------------------------------------------------

    if opcao.startswith("horario_"):

        try:
            horario_texto = opcao.removeprefix(
                "horario_"
            )

            horario_escolhido = datetime.strptime(
                horario_texto,
                "%H:%M"
            ).time()

            if not all([
                cliente_id,
                servico_id,
                profissional_id,
                data_agendamento
            ]):
                return resposta(
                    "Os dados do agendamento estão incompletos. Comece novamente.",
                    "inicio",
                    status=400
                )

            cliente = buscar_cliente(cliente_id)

            if not cliente:
                return resposta(
                    "Não consegui identificar seu cadastro. Faça login novamente.",
                    "identificacao",
                    [
                        {
                            "id": "login",
                            "texto": "Já tenho cadastro"
                        },
                        {
                            "id": "cadastro",
                            "texto": "Fazer cadastro"
                        }
                    ],
                    cliente_id=None,
                    status=400
                )

            servico = buscar_servico(servico_id)

            if not servico:
                return resposta(
                    "O serviço escolhido não está mais disponível.",
                    "agendamento_servico",
                    listar_opcoes_servicos(),
                    status=400
                )

            profissional = buscar_profissional(
                profissional_id,
                servico_id
            )

            if not profissional:
                return resposta(
                    "O profissional escolhido não está disponível.",
                    "agendamento_profissional",
                    buscar_profissionais(servico_id),
                    status=400
                )

            data_escolhida = date.fromisoformat(
                data_agendamento
            )

            # Verifica novamente o tipo de cabelo para Corte.
            if (
                servico["nome"].strip().lower() == "corte"
                and tipo_cabelo not in TIPOS_CABELO.values()
            ):
                return resposta(
                    "Informe novamente o tipo de cabelo.",
                    "agendamento_tipo_cabelo",
                    [
                        {
                            "id": chave,
                            "texto": valor
                        }
                        for chave, valor in TIPOS_CABELO.items()
                    ],
                    status=400
                )

            # Reconsulta a disponibilidade antes de salvar.
            horarios_atualizados = consultar_horarios_disponiveis(
                profissional_id,
                servico_id,
                data_escolhida
            )

            horario_id = f"horario_{horario_texto}"

            if not any(
                horario["id"] == horario_id
                for horario in horarios_atualizados
            ):
                return resposta(
                    (
                        "Esse horário não está mais disponível. "
                        "Escolha outro:"
                    ),
                    "agendamento_horario",
                    horarios_atualizados,
                    cliente_id=cliente_id,
                    servico_id=servico_id,
                    profissional_id=profissional_id,
                    tipo_cabelo=tipo_cabelo,
                    data_agendamento=data_agendamento
                )

            inicio = datetime.combine(
                data_escolhida,
                horario_escolhido
            )

            fim = inicio + timedelta(
                minutes=servico["duracao_minutos"]
            )

            # Insere o agendamento no Supabase.
            resultado = (
                supabase.table("agendamentos")
                .insert({
                    "cliente_id": cliente_id,
                    "profissional_id": profissional_id,
                    "servico_id": servico_id,
                    "tipo_cabelo": tipo_cabelo,
                    "data_hora_inicio": inicio.isoformat(),
                    "data_hora_fim": fim.isoformat(),
                    "status": "Confirmado"
                })
                .execute()
            )

            if not resultado.data:
                raise RuntimeError(
                    "O banco não retornou o agendamento criado."
                )

            agendamento = resultado.data[0]

            nome_profissional = NOMES_PROFISSIONAIS.get(
                profissional_id,
                {}
            ).get("nome", "Profissional")

            preco = float(servico["preco"])

            preco_formatado = (
                f"R$ {preco:.2f}".replace(".", ",")
            )

            return resposta(
                (
                    "Seu agendamento foi confirmado!\n\n"
                    f"Serviço: {servico['nome']}\n"
                    f"Profissional: {nome_profissional}\n"
                    f"Data: {inicio.strftime('%d/%m/%Y')}\n"
                    f"Horário: {inicio.strftime('%H:%M')} às "
                    f"{fim.strftime('%H:%M')}\n"
                    f"Valor: {preco_formatado}"
                ),
                "agendamento_confirmado",
                [
                    {
                        "id": "agendar",
                        "texto": "Fazer outro agendamento"
                    },
                    {
                        "id": "ver_agendamentos",
                        "texto": "Ver meus agendamentos"
                    }
                ],
                cliente_id=cliente_id,
                agendamento_id=agendamento["id"],
                servico_id=None,
                profissional_id=None,
                tipo_cabelo=None,
                data_agendamento=None
            )

        except ValueError as erro:
            return resposta(
                str(erro),
                "agendamento_horario",
                status=400
            )

        except Exception as erro:
            print("Erro ao salvar agendamento:", erro)

            return resposta(
                (
                    "Não foi possível concluir o agendamento. "
                    "Verifique os dados e tente novamente."
                ),
                "agendamento_horario",
                status=500
            )

    # -----------------------------------------------------
    # OPÇÃO NÃO RECONHECIDA
    # -----------------------------------------------------

    return resposta(
        "Opção não reconhecida. Vamos começar novamente.",
        "inicio",
        [
            {
                "id": "agendar",
                "texto": "Agendar"
            },
            {
                "id": "ver_agendamentos",
                "texto": "Ver meus agendamentos"
            }
        ],
        status=400
    )


# =========================================================
# 9. COMANDOS GLOBAIS DE TEXTO
# =========================================================

def processar_comando_global(comando, etapa, dados):
    """
    Processa comandos que podem ser digitados em qualquer etapa.

    Retorna uma resposta quando reconhece um comando.
    Retorna None quando deve continuar o fluxo normal.
    """

    cliente_id = obter_id_inteiro(
        dados.get("cliente_id")
    )

    servico_id = obter_id_inteiro(
        dados.get("servico_id")
    )

    profissional_id = obter_id_inteiro(
        dados.get("profissional_id")
    )

    tipo_cabelo = dados.get("tipo_cabelo")
    data_agendamento = dados.get("data_agendamento")

    # -----------------------------------------------------
    # SAUDAÇÕES
    # -----------------------------------------------------

    if (
        comando in (
            "oi",
            "ola",
            "bom dia",
            "boa tarde",
            "boa noite"
        )
        or comando.startswith((
            "oi ",
            "ola ",
            "bom dia ",
            "boa tarde ",
            "boa noite "
        ))
    ):
        return resposta(
            (
                "Oi! Tudo bem? Eu sou o chatbot oficial do AgendaCorte, "
                "desenvolvido pela CortesLabs. "
                "Estou aqui para ajudar você com seus agendamentos. "
                "Como posso ajudar?"
            ),
            "inicio",
            [
                {
                    "id": "agendar",
                    "texto": "Agendar horário"
                },
                {
                    "id": "ver_agendamentos",
                    "texto": "Consultar agendamentos"
                }
            ],
            cliente_id=cliente_id,
            servico_id=None,
            profissional_id=None,
            tipo_cabelo=None,
            data_agendamento=None
        )

    # -----------------------------------------------------
    # FINALIZAR ATENDIMENTO
    # -----------------------------------------------------

    if comando in (
        "finalizar",
        "encerrar",
        "fim",
        "terminar"
    ):
        return resposta(
            (
                "Atendimento finalizado! Obrigado por utilizar "
                "o AgendaCorte. Até a próxima!"
            ),
            "inicio",
            [
                {
                    "id": "agendar",
                    "texto": "Novo agendamento"
                },
                {
                    "id": "ver_agendamentos",
                    "texto": "Consultar agendamentos"
                }
            ],
            cliente_id=cliente_id,
            servico_id=None,
            profissional_id=None,
            tipo_cabelo=None,
            data_agendamento=None,
            finalizar=True
        )

    # -----------------------------------------------------
    # SAIR DA CONTA
    # -----------------------------------------------------

    if comando in (
        "sair da conta",
        "logout",
        "deslogar",
        "sair"
    ):
        return resposta(
            (
                "Você saiu da sua conta! Seu cadastro e seu histórico "
                "de agendamentos continuam salvos. "
                "Quando quiser, poderá entrar novamente."
            ),
            "inicio",
            [
                {
                    "id": "login",
                    "texto": "Entrar na minha conta"
                },
                {
                    "id": "cadastro",
                    "texto": "Fazer cadastro"
                }
            ],
            cliente_id=None,
            nome=None,
            logout=True,
            servico_id=None,
            profissional_id=None,
            tipo_cabelo=None,
            data_agendamento=None
        )

    # -----------------------------------------------------
    # FALAR COM ATENDENTE
    # -----------------------------------------------------

    if comando in (
        "falar com atendente",
        "falar com uma pessoa",
        "atendente",
        "atendimento humano",
        "quero falar com atendente"
    ):
        return resposta(
            (
                "No momento, nosso atendimento com um atendente "
                "não está disponível. Por favor, tente novamente "
                "mais tarde. Enquanto isso, posso ajudar você "
                "com os serviços e agendamentos por aqui."
            ),
            etapa or "inicio",
            cliente_id=cliente_id,
            servico_id=servico_id,
            profissional_id=profissional_id,
            tipo_cabelo=tipo_cabelo,
            data_agendamento=data_agendamento
        )

    # -----------------------------------------------------
    # PAGAMENTO
    # -----------------------------------------------------

    comandos_pagamento = (
        "pagar",
        "pagamento",
        "fazer pagamento",
        "pix",
        "pagar com pix",
        "formas de pagamento",
        "como pagar",
        "quero pagar"
    )

    if (
        comando in comandos_pagamento
        or comando.startswith((
            "pagar ",
            "pagamento ",
            "pix "
        ))
    ):
        return resposta(
            (
                "O pagamento deve ser realizado diretamente no caixa "
                "do salão. Aceitamos PIX, cédulas (dinheiro), cartões "
                "e vale-presente."
            ),
            etapa or "inicio",
            cliente_id=cliente_id,
            servico_id=servico_id,
            profissional_id=profissional_id,
            tipo_cabelo=tipo_cabelo,
            data_agendamento=data_agendamento
        )

    # -----------------------------------------------------
    # VOLTAR UMA ETAPA
    # -----------------------------------------------------

    if comando in (
        "voltar",
        "voltar etapa",
        "anterior"
    ):

        if etapa == "agendamento_profissional":
            return resposta(
                "Vamos voltar. Escolha novamente o serviço desejado:",
                "agendamento_servico",
                listar_opcoes_servicos(),
                cliente_id=cliente_id,
                servico_id=None,
                profissional_id=None,
                tipo_cabelo=None,
                data_agendamento=None
            )

        if etapa == "agendamento_data":
            return resposta(
                "Vamos voltar. Escolha novamente o profissional:",
                "agendamento_profissional",
                buscar_profissionais(servico_id),
                cliente_id=cliente_id,
                servico_id=servico_id,
                profissional_id=None,
                tipo_cabelo=tipo_cabelo,
                data_agendamento=None
            )

        if etapa == "agendamento_horario":
            return resposta(
                "Vamos voltar. Escolha novamente a data:",
                "agendamento_data",
                gerar_datas_disponiveis(),
                cliente_id=cliente_id,
                servico_id=servico_id,
                profissional_id=profissional_id,
                tipo_cabelo=tipo_cabelo,
                data_agendamento=None
            )

        if etapa == "agendamento_tipo_cabelo":
            return resposta(
                "Vamos voltar. Escolha novamente o serviço:",
                "agendamento_servico",
                listar_opcoes_servicos(),
                cliente_id=cliente_id,
                servico_id=None,
                profissional_id=None,
                tipo_cabelo=None,
                data_agendamento=None
            )

        if etapa == "agendamento_servico":
            return resposta(
                "Você voltou ao menu principal. O que deseja fazer?",
                "inicio",
                [
                    {
                        "id": "agendar",
                        "texto": "Agendar"
                    },
                    {
                        "id": "ver_agendamentos",
                        "texto": "Ver meus agendamentos"
                    }
                ],
                cliente_id=cliente_id,
                servico_id=None,
                profissional_id=None,
                tipo_cabelo=None,
                data_agendamento=None
            )

        if etapa == "login_telefone":
            return resposta(
                "Vamos voltar. Escolha como deseja acessar sua conta:",
                "identificacao",
                [
                    {
                        "id": "login",
                        "texto": "Já tenho cadastro"
                    },
                    {
                        "id": "cadastro",
                        "texto": "Fazer cadastro"
                    }
                ]
            )

        if etapa == "cadastro_nome":
            return resposta(
                "Vamos voltar. Você já possui cadastro?",
                "identificacao",
                [
                    {
                        "id": "login",
                        "texto": "Já tenho cadastro"
                    },
                    {
                        "id": "cadastro",
                        "texto": "Fazer cadastro"
                    }
                ]
            )

        if etapa == "cadastro_nascimento":
            return resposta(
                "Informe novamente seu nome completo:",
                "cadastro_nome"
            )

        if etapa == "cadastro_telefone":
            return resposta(
                (
                    "Informe novamente sua data de nascimento "
                    "no formato DD/MM/AAAA:"
                ),
                "cadastro_nascimento",
                nome=dados.get("nome")
            )

        if etapa == "identificacao":
            return resposta(
                "Você está na tela de acesso. Escolha uma opção:",
                "identificacao",
                [
                    {
                        "id": "login",
                        "texto": "Já tenho cadastro"
                    },
                    {
                        "id": "cadastro",
                        "texto": "Fazer cadastro"
                    }
                ]
            )
            if etapa in (
                    "consultar_agendamentos",
                    "cancelar_agendamento_confirmacao"
                ):
                    try:
                        opcoes = consultar_agendamentos_cliente(
                            cliente_id
                        ) if cliente_id else []

                        return resposta(
                            "Você voltou para seus agendamentos. Escolha um deles:",
                            "consultar_agendamentos",
                            opcoes + [
                                {
                                    "id": "agendar",
                                    "texto": "Fazer outro agendamento"
                                }
                            ],
                            cliente_id=cliente_id
                        )

                    except Exception as erro:
                        print("Erro ao voltar para agendamentos:", erro)

                        return resposta(
                            "Não foi possível carregar seus agendamentos.",
                            "inicio",
                            status=500
                        )

        
        return resposta(
            "Você já está no início. Como posso ajudar?",
            "inicio",
            [
                {
                    "id": "agendar",
                    "texto": "Agendar"
                },
                {
                    "id": "ver_agendamentos",
                    "texto": "Ver meus agendamentos"
                }
            ],
            cliente_id=cliente_id
        )

    # -----------------------------------------------------
    # COMEÇAR AGENDAMENTO POR TEXTO
    # -----------------------------------------------------

    comandos_agendamento = (
        "agendar",
        "agendamento",
        "fazer agendamento",
        "fazer um agendamento",
        "quero agendar",
        "marcar horario",
        "marcar um horario"
    )

    if comando in comandos_agendamento:

        cliente = buscar_cliente(cliente_id) if cliente_id else None

        if not cliente:
            return resposta(
                (
                    "Antes de agendar, preciso identificar você. "
                    "Escolha uma opção:"
                ),
                "identificacao",
                [
                    {
                        "id": "login",
                        "texto": "Já tenho cadastro"
                    },
                    {
                        "id": "cadastro",
                        "texto": "Quero me cadastrar"
                    }
                ],
                cliente_id=None
            )

        return resposta(
            (
                f"Certo, {cliente['nome_completo']}! "
                "Vamos começar seu agendamento. "
                "Escolha o serviço desejado:"
            ),
            "agendamento_servico",
            listar_opcoes_servicos(),
            cliente_id=cliente["id"],
            servico_id=None,
            profissional_id=None,
            tipo_cabelo=None,
            data_agendamento=None
        )

    # -----------------------------------------------------
    # ABRIR LOGIN OU CADASTRO POR TEXTO
    # -----------------------------------------------------

    comandos_acesso = (
        "login",
        "entrar",
        "fazer login",
        "cadastro",
        "cadastrar",
        "fazer cadastro",
        "registrar",
        "criar conta"
    )

    if comando in comandos_acesso:
        return resposta(
            "Para continuar, escolha como deseja acessar o AgendaCorte:",
            "identificacao",
            [
                {
                    "id": "login",
                    "texto": "Já tenho cadastro"
                },
                {
                    "id": "cadastro",
                    "texto": "Fazer cadastro"
                }
            ],
            cliente_id=None,
            servico_id=None,
            profissional_id=None,
            tipo_cabelo=None,
            data_agendamento=None
        )

    # Não reconheceu um comando global.
    return None


# =========================================================
# 10. RECEBER MENSAGENS DIGITADAS
# =========================================================

@chat_bp.route("/mensagem", methods=["POST"])
def receber_mensagem():
    """
    Recebe mensagens digitadas pelo usuário.

    Primeiro verifica os comandos globais.
    Se não encontrar um comando, continua a etapa atual.
    """

    dados = request.get_json(silent=True) or {}

    etapa = dados.get("etapa") or "inicio"
    texto = dados.get("texto", "")

    if not isinstance(texto, str) or not texto.strip():
        return resposta(
            "Digite uma informação.",
            etapa,
            status=400
        )

    texto = texto.strip()

    comando = normalizar_comando(texto)

    # -----------------------------------------------------
    # PRIMEIRO: VERIFICAR COMANDOS GLOBAIS
    # -----------------------------------------------------

    try:
        resultado_global = processar_comando_global(
            comando,
            etapa,
            dados
        )

        if resultado_global is not None:
            return resultado_global

    except Exception as erro:
        print("Erro ao processar comando global:", erro)

        return resposta(
            "Não foi possível processar esse comando. Tente novamente.",
            etapa,
            status=500
        )

    # -----------------------------------------------------
    # LOGIN: TELEFONE
    # -----------------------------------------------------

    if etapa == "login_telefone":

        telefone = validar_telefone(texto)

        if not telefone:
            return resposta(
                (
                    "Telefone inválido. Informe o DDD "
                    "e 10 ou 11 dígitos."
                ),
                "login_telefone"
            )

        try:
            cliente = buscar_cliente_por_telefone(
                telefone
            )

            if not cliente:
                return resposta(
                    (
                        "Não encontrei um cadastro com esse telefone. "
                        "Você pode tentar novamente ou se cadastrar."
                    ),
                    "telefone_nao_encontrado",
                    [
                        {
                            "id": "login",
                            "texto": "Tentar novamente"
                        },
                        {
                            "id": "cadastro",
                            "texto": "Fazer cadastro"
                        }
                    ]
                )

            return resposta(
                (
                    f"Olá novamente, {cliente['nome_completo']}! "
                    "Seu cadastro foi reconhecido. O que deseja fazer?"
                ),
                "identificado",
                [
                    {
                        "id": "agendar",
                        "texto": "Agendar horário"
                    },
                    {
                        "id": "ver_agendamentos",
                        "texto": "Consultar meus agendamentos"
                    },
                    {
                        "id": "trocar_usuario",
                        "texto": "Atender outra pessoa"
                    }
                ],
                cliente_id=cliente["id"],
                nome=cliente["nome_completo"]
            )

        except Exception as erro:
            print("Erro ao consultar cliente:", erro)

            return resposta(
                "Não foi possível consultar seu cadastro. Tente novamente.",
                "login_telefone",
                status=500
            )

    # -----------------------------------------------------
    # CADASTRO: NOME
    # -----------------------------------------------------

    if etapa == "cadastro_nome":

        if not validar_nome(texto):
            return resposta(
                (
                    "Nome inválido. Informe seu nome completo "
                    "usando letras e espaços."
                ),
                "cadastro_nome"
            )

        return resposta(
            (
                f"Obrigado, {texto}! Agora informe sua data "
                "de nascimento no formato DD/MM/AAAA."
            ),
            "cadastro_nascimento",
            nome=texto
        )

    # -----------------------------------------------------
    # CADASTRO: DATA DE NASCIMENTO
    # -----------------------------------------------------

    if etapa == "cadastro_nascimento":

        data_validada = validar_data_nascimento(
            texto
        )

        if not data_validada:
            return resposta(
                (
                    "Data inválida. Informe uma data existente "
                    "no formato DD/MM/AAAA. Exemplo: 12/12/2005."
                ),
                "cadastro_nascimento"
            )

        return resposta(
            (
                f"Data recebida: {data_validada['formatada']}. "
                "Agora informe seu telefone com DDD."
            ),
            "cadastro_telefone",
            data_nascimento=data_validada["banco"]
        )

    # -----------------------------------------------------
    # CADASTRO: TELEFONE E SALVAMENTO
    # -----------------------------------------------------

    if etapa == "cadastro_telefone":

        telefone = validar_telefone(texto)

        if not telefone:
            return resposta(
                (
                    "Telefone inválido. Informe o DDD "
                    "e 10 ou 11 dígitos."
                ),
                "cadastro_telefone"
            )

        nome = dados.get("nome")
        nascimento = dados.get("data_nascimento")

        if not validar_nome(nome):
            return resposta(
                "Não consegui recuperar seu nome. Informe novamente.",
                "cadastro_nome"
            )

        try:
            data_nascimento = datetime.strptime(
                nascimento,
                "%Y-%m-%d"
            ).date()

            if data_nascimento > date.today():
                raise ValueError("Data futura.")

        except (ValueError, TypeError):
            return resposta(
                "Data de nascimento inválida. Informe novamente.",
                "cadastro_nascimento"
            )

        try:
            existente = buscar_cliente_por_telefone(
                telefone
            )

            if existente:
                return resposta(
                    (
                        "Este telefone já está cadastrado. "
                        "Entre utilizando seu número."
                    ),
                    "login_telefone"
                )

            resultado = (
                supabase.table("clientes")
                .insert({
                    "nome_completo": nome.strip(),
                    "data_nascimento": data_nascimento.isoformat(),
                    "celular": telefone
                })
                .execute()
            )

            if not resultado.data:
                raise RuntimeError(
                    "O banco não retornou o cliente cadastrado."
                )

            cliente = resultado.data[0]

            return resposta(
                (
                    f"Cadastro concluído, {cliente['nome_completo']}! "
                    "Agora escolha o que deseja fazer."
                ),
                "identificado",
                [
                    {
                        "id": "agendar",
                        "texto": "Agendar horário"
                    },
                    {
                        "id": "ver_agendamentos",
                        "texto": "Consultar meus agendamentos"
                    }
                ],
                cliente_id=cliente["id"],
                nome=cliente["nome_completo"]
            )

        except Exception as erro:
            print("Erro ao cadastrar cliente:", erro)

            return resposta(
                "Não foi possível concluir seu cadastro. Tente novamente.",
                "cadastro_telefone",
                status=500
            )

    # -----------------------------------------------------
    # ETAPA NÃO RECONHECIDA
    # -----------------------------------------------------

    return resposta(
        (
            "Não consegui identificar a etapa atual. "
            "Vamos começar novamente."
        ),
        "inicio",
        [
            {
                "id": "agendar",
                "texto": "Agendar"
            },
            {
                "id": "ver_agendamentos",
                "texto": "Ver meus agendamentos"
            }
        ],
        status=400
    )
