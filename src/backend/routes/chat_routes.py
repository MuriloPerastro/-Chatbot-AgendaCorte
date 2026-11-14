
import re
from datetime import datetime, date

from flask import Blueprint, jsonify, request
from ..database import supabase


chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================

def normalizar_telefone(telefone):
    return "".join(
        caractere
        for caractere in telefone
        if caractere.isdigit()
    )


def validar_nome(nome):
    nome = nome.strip()

    padrao = r"^[^\W\d_]+(?:[ '-][^\W\d_]+)*$"

    return (
        len(nome) >= 3
        and re.fullmatch(padrao, nome) is not None
    )


def validar_data(texto):
    texto = texto.strip()

    if re.fullmatch(r"\d{8}", texto):
        data_formatada = (
            f"{texto[:2]}/{texto[2:4]}/{texto[4:]}"
        )

    elif re.fullmatch(r"\d{2}/\d{2}/\d{4}", texto):
        data_formatada = texto

    else:
        return None

    try:
        data_validada = datetime.strptime(
            data_formatada,
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


def validar_telefone(texto):
    if not re.fullmatch(r"[0-9\s()+.-]+", texto):
        return None

    telefone = normalizar_telefone(texto)

    if len(telefone) not in [10, 11]:
        return None

    return telefone


# Busca os profissionais vinculados a um serviço.

def buscar_profissionais(servico_id):
    vinculos = (
        supabase.table("profissional_servicos")
        .select("profissional_id")
        .eq("servico_id", servico_id)
        .execute()
    )

    ids_profissionais = list({
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
        .order("id")
        .execute()
    )

    nomes = {
        1: {"nome": "Rodrigo", "imagem": "Rodrigo.png"},
        2: {"nome": "Cleber", "imagem": "Cleber.png"},
        3: {"nome": "Carina", "imagem": "Carina.png"}
    }

    profissionais = []

    for profissional in resultado.data or []:
        identificacao = nomes.get(profissional["id"])

        if identificacao:
            profissionais.append({
                "id": f"profissional_{profissional['id']}",
                "texto": identificacao["nome"],
                "imagem": identificacao["imagem"]
            })

    return profissionais


# =========================================================
# INICIAR CONVERSA
# =========================================================

@chat_bp.route("/iniciar", methods=["GET"])
def iniciar_conversa():
    return jsonify({
        "mensagem": "Olá! Tudo bem? Como posso te ajudar?",
        "etapa": "inicio",
        "opcoes": [
            {"id": "agendar", "texto": "Agendar"},
            {
                "id": "ver_agendamentos",
                "texto": "Ver meus agendamentos"
            }
        ]
    })


# =========================================================
# PROCESSAR OPÇÕES DOS BOTÕES
# =========================================================

@chat_bp.route("/responder", methods=["POST"])
def responder():
    dados = request.get_json(silent=True) or {}

    opcao = dados.get("opcao")
    cliente_id = dados.get("cliente_id")
    servico_id = dados.get("servico_id")

    if not isinstance(opcao, str) or not opcao:
        return jsonify({
            "erro": "Nenhuma opção foi enviada."
        }), 400

    # -----------------------------------------------------
    # SELEÇÃO DO SERVIÇO
    # -----------------------------------------------------

    if opcao.startswith("servico_"):
        try:
            identificador = opcao.replace("servico_", "", 1)

            if not identificador.isdigit():
                return jsonify({
                    "mensagem": "Serviço inválido.",
                    "etapa": "agendamento_servico",
                    "opcoes": []
                }), 400

            servico_id = int(identificador)

            resultado = (
                supabase.table("servicos")
                .select("id, nome, preco, duracao_minutos")
                .eq("id", servico_id)
                .limit(1)
                .execute()
            )

            if not resultado.data:
                return jsonify({
                    "mensagem": "Esse serviço não foi encontrado.",
                    "etapa": "agendamento_servico",
                    "opcoes": []
                }), 404

            servico = resultado.data[0]

            # Corte precisa perguntar o tipo de cabelo.
            if servico["nome"].strip().lower() == "corte":
                return jsonify({
                    "mensagem": (
                        "Certo! Antes de continuar, "
                        "qual é o tipo atual do seu cabelo?"
                    ),
                    "cliente_id": cliente_id,
                    "servico_id": servico["id"],
                    "etapa": "agendamento_tipo_cabelo",
                    "opcoes": [
                        {
                            "id": "cabelo_natural",
                            "texto": "Natural"
                        },
                        {
                            "id": "cabelo_descolorido",
                            "texto": "Com descoloração"
                        },
                        {
                            "id": "cabelo_tingido",
                            "texto": "Com tintura"
                        },
                        {
                            "id": "cabelo_outro",
                            "texto": "Outros"
                        }
                    ]
                })

            # Química e Tratamento seguem para os profissionais.
            opcoes_profissionais = buscar_profissionais(
                servico["id"]
            )

            if not opcoes_profissionais:
                return jsonify({
                    "mensagem": (
                        "Não encontramos profissionais "
                        "disponíveis para esse serviço."
                    ),
                    "cliente_id": cliente_id,
                    "servico_id": servico["id"],
                    "etapa": "agendamento_profissional",
                    "opcoes": []
                })

            return jsonify({
                "mensagem": (
                    f"Você escolheu {servico['nome']}. "
                    "Agora escolha o profissional:"
                ),
                "cliente_id": cliente_id,
                "servico_id": servico["id"],
                "etapa": "agendamento_profissional",
                "opcoes": opcoes_profissionais
            })

        except Exception as erro:
            print("Erro ao selecionar serviço:", erro)

            return jsonify({
                "mensagem": "Não foi possível selecionar esse serviço.",
                "etapa": "agendamento_servico",
                "opcoes": []
            }), 500

    # -----------------------------------------------------
    # SELEÇÃO DO TIPO DE CABELO
    # -----------------------------------------------------

    tipos_cabelo = {
        "cabelo_natural": "Natural",
        "cabelo_descolorido": "Com descoloração",
        "cabelo_tingido": "Com tintura",
        "cabelo_outro": "Outros"
    }

    if opcao in tipos_cabelo:
        try:
            if not servico_id:
                return jsonify({
                    "mensagem": (
                        "Não consegui identificar o serviço escolhido. "
                        "Vamos começar novamente."
                    ),
                    "etapa": "agendamento_servico",
                    "opcoes": []
                }), 400

            servico_id = int(servico_id)

            resultado = (
                supabase.table("servicos")
                .select("id, nome")
                .eq("id", servico_id)
                .limit(1)
                .execute()
            )

            if not resultado.data:
                return jsonify({
                    "mensagem": "Serviço não encontrado.",
                    "etapa": "agendamento_servico",
                    "opcoes": []
                }), 404

            servico = resultado.data[0]

            if servico["nome"].strip().lower() != "corte":
                return jsonify({
                    "mensagem": (
                        "Essa opção de cabelo não se aplica "
                        "ao serviço escolhido."
                    ),
                    "etapa": "agendamento_servico",
                    "opcoes": []
                }), 400

            tipo_cabelo = tipos_cabelo[opcao]

            opcoes_profissionais = buscar_profissionais(
                servico["id"]
            )

            if not opcoes_profissionais:
                return jsonify({
                    "mensagem": (
                        "Não encontramos profissionais "
                        "disponíveis para esse serviço."
                    ),
                    "cliente_id": cliente_id,
                    "servico_id": servico["id"],
                    "tipo_cabelo": tipo_cabelo,
                    "etapa": "agendamento_profissional",
                    "opcoes": []
                })

            return jsonify({
                "mensagem": (
                    f"Entendido! Tipo de cabelo: {tipo_cabelo}. "
                    "Agora escolha o profissional:"
                ),
                "cliente_id": cliente_id,
                "servico_id": servico["id"],
                "tipo_cabelo": tipo_cabelo,
                "etapa": "agendamento_profissional",
                "opcoes": opcoes_profissionais
            })

        except (ValueError, TypeError):
            return jsonify({
                "mensagem": "Identificação do serviço inválida.",
                "etapa": "agendamento_servico",
                "opcoes": []
            }), 400

        except Exception as erro:
            print("Erro ao selecionar tipo de cabelo:", erro)

            return jsonify({
                "mensagem": "Não foi possível registrar essa informação.",
                "etapa": "agendamento_tipo_cabelo",
                "opcoes": []
            }), 500

    # -----------------------------------------------------
    # SELEÇÃO DO PROFISSIONAL
    # -----------------------------------------------------

    if opcao.startswith("profissional_"):
        try:
            identificador = opcao.replace(
                "profissional_", "", 1
            )

            if not identificador.isdigit() or not servico_id:
                return jsonify({
                    "mensagem": "Não foi possível identificar o profissional ou serviço.",
                    "etapa": "agendamento_profissional",
                    "opcoes": []
                }), 400

            profissional_id = int(identificador)
            servico_id = int(servico_id)

            vinculo = (
                supabase.table("profissional_servicos")
                .select("profissional_id")
                .eq("profissional_id", profissional_id)
                .eq("servico_id", servico_id)
                .execute()
            )

            if not vinculo.data:
                return jsonify({
                    "mensagem": "Esse profissional não atende o serviço escolhido.",
                    "etapa": "agendamento_profissional",
                    "opcoes": []
                }), 400

            profissional = (
                supabase.table("profissionais")
                .select("id, nome")
                .eq("id", profissional_id)
                .eq("ativo", True)
                .limit(1)
                .execute()
            )

            if not profissional.data:
                return jsonify({
                    "mensagem": "Esse profissional não está disponível.",
                    "etapa": "agendamento_profissional",
                    "opcoes": []
                }), 404

            return jsonify({
                "mensagem": (
                    f"Você escolheu {profissional.data[0]['nome']}. "
                    "Agora vamos escolher a data do atendimento."
                ),
                "cliente_id": cliente_id,
                "servico_id": servico_id,
                "profissional_id": profissional_id,
                "tipo_cabelo": dados.get("tipo_cabelo"),
                "etapa": "agendamento_data",
                "opcoes": []
            })

        except Exception as erro:
            print("Erro ao selecionar profissional:", erro)

            return jsonify({
                "mensagem": "Não foi possível selecionar esse profissional.",
                "etapa": "agendamento_profissional",
                "opcoes": []
            }), 500
    
    # Seleção do profissional
    if opcao.startswith("profissional_"):
        try:
            identificador = opcao.replace("profissional_", "", 1)

            if not identificador.isdigit():
                return jsonify({
                    "mensagem": "Profissional inválido.",
                    "etapa": "agendamento_profissional",
                    "opcoes": []
                }), 400

            profissional_id = int(identificador)

            if not servico_id:
                return jsonify({
                    "mensagem": "Não consegui identificar o serviço escolhido.",
                    "etapa": "agendamento_servico",
                    "opcoes": []
                }), 400

            # Confirma se o profissional está ativo.
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
                    "mensagem": "Profissional não encontrado.",
                    "etapa": "agendamento_profissional",
                    "opcoes": []
                }), 404

            # Confirma se ele atende o serviço escolhido.
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
                    "mensagem": "Esse profissional não atende o serviço escolhido.",
                    "etapa": "agendamento_profissional",
                    "opcoes": []
                }), 400

            nomes = {
                1: "Rodrigo",
                2: "Cleber",
                3: "Carina"
            }

            nome_profissional = nomes.get(
                profissional_id,
                "Profissional"
            )

            # Gerar os próximos 10 dias úteis.
            from datetime import timedelta

            opcoes_datas = []
            dia = date.today()

            while len(opcoes_datas) < 10:
                dia += timedelta(days=1)

                if dia.weekday() < 5:
                    opcoes_datas.append({
                        "id": f"data_{dia.isoformat()}",
                        "texto": dia.strftime("%d/%m/%Y")
                    })

            return jsonify({
                "mensagem": (
                    f"Você escolheu {nome_profissional}! "
                    "Agora escolha a data do atendimento:"
                ),
                "cliente_id": cliente_id,
                "servico_id": servico_id,
                "tipo_cabelo": dados.get("tipo_cabelo"),
                "profissional_id": profissional_id,
                "etapa": "agendamento_data",
                "opcoes": opcoes_datas
            })

        except Exception as erro:
            print("Erro ao selecionar profissional:", erro)

            return jsonify({
                "mensagem": "Não foi possível selecionar o profissional.",
                "etapa": "agendamento_profissional",
                "opcoes": []
            }), 500


    # -----------------------------------------------------
    # TROCAR DE USUÁRIO
    # -----------------------------------------------------

    if opcao == "trocar_usuario":
        return jsonify({
            "mensagem": "Quem vai utilizar o AgendaCorte agora?",
            "etapa": "identificacao",
            "opcoes": [
                {"id": "login", "texto": "Já tenho cadastro"},
                {"id": "cadastro", "texto": "Fazer cadastro"}
            ]
        })

    # -----------------------------------------------------
    # AGENDAR OU CONSULTAR AGENDAMENTOS
    # -----------------------------------------------------

    if opcao in ["agendar", "ver_agendamentos"]:
        if cliente_id:
            try:
                resultado = (
                    supabase.table("clientes")
                    .select("id, nome_completo")
                    .eq("id", cliente_id)
                    .limit(1)
                    .execute()
                )

                if resultado.data:
                    cliente = resultado.data[0]

                    if opcao == "agendar":
                        resultado = (
                            supabase.table("servicos")
                            .select(
                                "id, nome, preco, duracao_minutos"
                            )
                            .order("nome")
                            .execute()
                        )

                        servicos = resultado.data or []

                        if not servicos:
                            return jsonify({
                                "mensagem": (
                                    "No momento, não temos "
                                    "serviços disponíveis."
                                ),
                                "cliente_id": cliente["id"],
                                "etapa": "agendamento_servico",
                                "opcoes": []
                            })

                        opcoes_servicos = []

                        for servico in servicos:
                            preco = float(servico["preco"])
                            preco_formatado = (
                                f"R$ {preco:.2f}".replace(".", ",")
                            )

                            duracao = (
                                servico["duracao_minutos"] or 30
                            )

                            opcoes_servicos.append({
                                "id": f"servico_{servico['id']}",
                                "texto": (
                                    f"{servico['nome']} — "
                                    f"{preco_formatado} "
                                    f"({duracao} minutos)"
                                )
                            })

                        return jsonify({
                            "mensagem": (
                                f"Certo, {cliente['nome_completo']}! "
                                "Vamos começar seu agendamento. "
                                "Escolha um dos serviços disponíveis:"
                            ),
                            "cliente_id": cliente["id"],
                            "etapa": "agendamento_servico",
                            "opcoes": opcoes_servicos
                        })

                    return jsonify({
                        "mensagem": (
                            f"Olá, {cliente['nome_completo']}! "
                            "Vamos consultar seus agendamentos."
                        ),
                        "cliente_id": cliente["id"],
                        "etapa": "consultar_agendamentos",
                        "opcoes": [
                            {
                                "id": "trocar_usuario",
                                "texto": "Atender outra pessoa"
                            }
                        ]
                    })

            except Exception as erro:
                print("Erro ao verificar cliente:", erro)

                return jsonify({
                    "mensagem": (
                        "Erro ao verificar seu cadastro. "
                        "Tente novamente."
                    ),
                    "etapa": "identificado",
                    "opcoes": []
                }), 500

        return jsonify({
            "mensagem": (
                "Antes de continuar, preciso identificar você. "
                "Você já possui cadastro?"
            ),
            "etapa": "identificacao",
            "opcoes": [
                {"id": "login", "texto": "Já tenho cadastro"},
                {"id": "cadastro", "texto": "Quero me cadastrar"}
            ]
        })

    # -----------------------------------------------------
    # LOGIN
    # -----------------------------------------------------

    if opcao == "login":
        return jsonify({
            "mensagem": "Informe seu telefone com DDD.",
            "etapa": "login_telefone",
            "opcoes": []
        })

    # -----------------------------------------------------
    # CADASTRO
    # -----------------------------------------------------

    if opcao == "cadastro":
        return jsonify({
            "mensagem": "Informe seu nome completo.",
            "etapa": "cadastro_nome",
            "opcoes": []
        })

    return jsonify({
        "mensagem": "Opção não reconhecida.",
        "etapa": "inicio",
        "opcoes": [
            {"id": "agendar", "texto": "Agendar"},
            {
                "id": "ver_agendamentos",
                "texto": "Consultar agendamentos"
            }
        ]
    })


# =========================================================
# RECEBER MENSAGENS DO USUÁRIO
# =========================================================

@chat_bp.route("/mensagem", methods=["POST"])
def receber_mensagem():
    dados = request.get_json(silent=True) or {}

    etapa = dados.get("etapa")
    texto = dados.get("texto", "")

    if not isinstance(texto, str) or not texto.strip():
        return jsonify({
            "mensagem": "Digite uma informação.",
            "etapa": etapa,
            "opcoes": []
        }), 400

    texto = texto.strip()

    # -----------------------------------------------------
    # LOGIN: LOCALIZAR CLIENTE PELO TELEFONE
    # -----------------------------------------------------

    if etapa == "login_telefone":
        telefone = validar_telefone(texto)

        if not telefone:
            return jsonify({
                "mensagem": (
                    "Telefone inválido. Informe os números "
                    "com DDD, utilizando 10 ou 11 dígitos."
                ),
                "etapa": "login_telefone",
                "opcoes": []
            })

        try:
            resultado = (
                supabase.table("clientes")
                .select("id, nome_completo, celular")
                .eq("celular", telefone)
                .execute()
            )

            if resultado.data:
                cliente = resultado.data[0]

                return jsonify({
                    "mensagem": (
                        f"Olá novamente, {cliente['nome_completo']}! "
                        "Seu cadastro foi reconhecido. "
                        "O que deseja fazer agora?"
                    ),
                    "cliente_id": cliente["id"],
                    "nome": cliente["nome_completo"],
                    "etapa": "identificado",
                    "opcoes": [
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
                    ]
                })

            return jsonify({
                "mensagem": (
                    "Não encontrei um cadastro com esse telefone. "
                    "Você pode tentar novamente ou iniciar um cadastro."
                ),
                "etapa": "telefone_nao_encontrado",
                "opcoes": [
                    {"id": "login", "texto": "Tentar novamente"},
                    {"id": "cadastro", "texto": "Fazer cadastro"}
                ]
            })

        except Exception as erro:
            print("Erro ao consultar cliente:", erro)

            return jsonify({
                "mensagem": (
                    "Não foi possível consultar o cadastro. "
                    "Tente novamente."
                ),
                "etapa": "login_telefone",
                "opcoes": []
            }), 500

    # -----------------------------------------------------
    # CADASTRO: RECEBER NOME
    # -----------------------------------------------------

    if etapa == "cadastro_nome":
        if not validar_nome(texto):
            return jsonify({
                "mensagem": (
                    "Nome inválido. Digite seu nome utilizando "
                    "somente letras, espaços e acentos."
                ),
                "etapa": "cadastro_nome",
                "opcoes": []
            })

        return jsonify({
            "mensagem": (
                f"Obrigado, {texto}! Agora informe sua data "
                "de nascimento no formato DD/MM/AAAA."
            ),
            "etapa": "cadastro_nascimento",
            "nome": texto,
            "opcoes": []
        })

    # -----------------------------------------------------
    # CADASTRO: RECEBER DATA DE NASCIMENTO
    # -----------------------------------------------------

    if etapa == "cadastro_nascimento":
        data_validada = validar_data(texto)

        if not data_validada:
            return jsonify({
                "mensagem": (
                    "Data inválida. Informe uma data existente "
                    "no formato DD/MM/AAAA ou apenas os 8 números. "
                    "Exemplo: 12122005."
                ),
                "etapa": "cadastro_nascimento",
                "opcoes": []
            })

        return jsonify({
            "mensagem": (
                f"Data recebida: {data_validada['formatada']}. "
                "Agora informe seu telefone com DDD."
            ),
            "etapa": "cadastro_telefone",
            "data_nascimento": data_validada["banco"],
            "opcoes": []
        })

    # -----------------------------------------------------
    # CADASTRO: RECEBER TELEFONE E SALVAR NO SUPABASE
    # -----------------------------------------------------

    if etapa == "cadastro_telefone":
        telefone = validar_telefone(texto)

        if not telefone:
            return jsonify({
                "mensagem": (
                    "Telefone inválido. Informe os números "
                    "com DDD, utilizando 10 ou 11 dígitos."
                ),
                "etapa": "cadastro_telefone",
                "opcoes": []
            })

        nome = dados.get("nome")
        nascimento = dados.get("data_nascimento")

        if not nome or not nascimento:
            return jsonify({
                "mensagem": (
                    "Não consegui recuperar seus dados. "
                    "Vamos iniciar o cadastro novamente."
                ),
                "etapa": "cadastro_nome",
                "opcoes": []
            })

        try:
            datetime.strptime(nascimento, "%Y-%m-%d")

        except (ValueError, TypeError):
            return jsonify({
                "mensagem": (
                    "Data de nascimento inválida. "
                    "Informe novamente sua data de nascimento."
                ),
                "etapa": "cadastro_nascimento",
                "opcoes": []
            })

        try:
            existente = (
                supabase.table("clientes")
                .select("id")
                .eq("celular", telefone)
                .execute()
            )

            if existente.data:
                return jsonify({
                    "mensagem": (
                        "Este telefone já está cadastrado. "
                        "Você pode entrar utilizando seu número."
                    ),
                    "etapa": "login_telefone",
                    "opcoes": []
                })

            resultado = (
                supabase.table("clientes")
                .insert({
                    "nome_completo": nome,
                    "data_nascimento": nascimento,
                    "celular": telefone
                })
                .execute()
            )

            if not resultado.data:
                raise Exception(
                    "O banco não retornou o cliente cadastrado."
                )

            cliente = resultado.data[0]

            return jsonify({
                "mensagem": (
                    f"Cadastro concluído, {cliente['nome_completo']}! "
                    "Agora você pode escolher o que deseja fazer."
                ),
                "etapa": "identificado",
                "cliente_id": cliente["id"],
                "nome": cliente["nome_completo"],
                "opcoes": [
                    {
                        "id": "agendar",
                        "texto": "Agendar horário"
                    },
                    {
                        "id": "ver_agendamentos",
                        "texto": "Consultar meus agendamentos"
                    }
                ]
            })

        except Exception as erro:
            print("Erro ao cadastrar cliente:", erro)

            return jsonify({
                "mensagem": (
                    "Não foi possível concluir seu cadastro. "
                    "Tente novamente."
                ),
                "etapa": "cadastro_telefone",
                "opcoes": []
            }), 500

    # -----------------------------------------------------
    # ETAPA NÃO RECONHECIDA
    # -----------------------------------------------------

    return jsonify({
        "mensagem": (
            "Não consegui identificar a etapa atual. "
            "Vamos começar novamente."
        ),
        "etapa": "inicio",
        "opcoes": [
            {"id": "agendar", "texto": "Agendar"},
            {
                "id": "ver_agendamentos",
                "texto": "Ver meus agendamentos"
            }
        ]
    })
