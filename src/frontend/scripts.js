
// =========================================================
// 1. ELEMENTOS DO HTML
// =========================================================

// Elementos principais do chatbot.
const mensagens = document.getElementById("chat-messages");
const botoes = document.getElementById("chat-buttons");
const formulario = document.getElementById("chat-form");
const campoTexto = document.getElementById("user-input");



// =========================================================
// 2. ESTADO DA CONVERSA
// =========================================================

// Guarda em qual etapa o usuário está.
let etapaAtual = "inicio";

// Dados utilizados durante o agendamento.
let servicoId = null;
let dataAgendamento = null;
let tipoCabelo = null;
let profissionalId = null;

// Dados utilizados no cadastro.
let nomeUsuario = localStorage.getItem("agendaCorteNome") || "";
let dataNascimento = null;

// Recupera o cliente salvo no navegador.
let clienteId = localStorage.getItem("agendaCorteClienteId");

if (clienteId) {
    clienteId = Number(clienteId);
}


// =========================================================
// 3. ADICIONAR MENSAGENS AO CHAT
// =========================================================


/* ========================================
   INDICADOR DE DIGITAÇÃO
======================================== */

// Guarda o momento em que o bot começou a processar.
let inicioDigitacao = 0;

// Mostra os três pontinhos animados.
function mostrarDigitando() {
    if (!mensagens) return;

    // Evita criar indicadores duplicados.
    removerDigitando();

    inicioDigitacao = Date.now();

    const indicador = document.createElement("div");
    indicador.classList.add("typing-message");
    indicador.id = "indicador-digitando";

    const avatar = document.createElement("img");
    avatar.src = "/assets/icone-app.jpg";
    avatar.alt = "AgendaCorte";
    avatar.classList.add("bot-avatar");

    const bolha = document.createElement("div");
    bolha.classList.add("typing-bubble");

    // Cria os três pontinhos.
    for (let i = 0; i < 3; i++) {
        const ponto = document.createElement("span");
        ponto.classList.add("typing-dot");
        bolha.appendChild(ponto);
    }

    indicador.appendChild(avatar);
    indicador.appendChild(bolha);

    mensagens.appendChild(indicador);
    mensagens.scrollTop = mensagens.scrollHeight;
}

// Remove os pontinhos.
function removerDigitando() {
    const indicador = document.getElementById(
        "indicador-digitando"
    );

    if (indicador) {
        indicador.remove();
    }
}


/* ========================================
   MENSAGENS DO CHAT
======================================== */

function adicionarMensagem(texto, tipo = "bot") {
    if (!mensagens) return null;

    const mensagem = document.createElement("div");

    mensagem.classList.add(
        "message",
        `${tipo}-message`,
        "mensagem",
        `mensagem-${tipo}`
    );

    // Avatar do chatbot.
    if (tipo === "bot") {
        const avatar = document.createElement("img");

        avatar.src = "/assets/icone-app.jpg";
        avatar.alt = "AgendaCorte";
        avatar.classList.add("bot-avatar");

        mensagem.appendChild(avatar);
    }

    // Conteúdo textual.
    const conteudo = document.createElement("div");
    conteudo.classList.add("message-content");
    conteudo.textContent = texto;

    mensagem.appendChild(conteudo);

    // Confirmação de envio para mensagens do usuário.
    if (tipo === "user") {
        const status = document.createElement("div");
        status.classList.add("message-status");

        const checks = document.createElement("span");
        checks.classList.add("check");
        checks.textContent = "✓✓";

        status.appendChild(checks);
        mensagem.appendChild(status);
    }

    mensagens.appendChild(mensagem);
    mensagens.scrollTop = mensagens.scrollHeight;

    // Retorna o elemento para atualizar os tiques depois.
    return mensagem;
}


/* ========================================
   CONFIRMAÇÃO DE RECEBIMENTO
======================================== */

function marcarComoRecebida(mensagem) {
    if (!mensagem) return;

    const status = mensagem.querySelector(".message-status");

    if (!status) return;

    // Aguarda meio segundo antes de deixar os tiques azuis.
    setTimeout(() => {
        status.classList.add("received");
    }, 500);
}


/* ========================================
   PROCESSAMENTO DA RESPOSTA
======================================== */

async function processarResposta(response) {
    try {
        const dados = await response.json();

        // Garante que os pontinhos apareçam por pelo menos 500 ms.
        const tempoDecorrido = Date.now() - inicioDigitacao;
        const tempoRestante = Math.max(0, 500 - tempoDecorrido);

        if (tempoRestante > 0) {
            await new Promise(resolve => {
                setTimeout(resolve, tempoRestante);
            });
        }

        // Remove o indicador antes de mostrar a resposta.
        removerDigitando();

        // Atualiza o estado da conversa.
        atualizarEstado(dados);

        // Exibe a mensagem do chatbot.
        if (dados.mensagem) {
            adicionarMensagem(dados.mensagem, "bot");
        }

        // Exibe os botões da nova etapa.
        mostrarOpcoes(dados.opcoes || []);

        // Mostra erros retornados pelo servidor no console.
        if (!response.ok) {
            console.error(
                "Erro retornado pelo servidor:",
                dados
            );
        }

        return dados;

    } catch (erro) {
        removerDigitando();
        throw erro;
    }
}


/* ========================================
   ENVIAR OPÇÃO DOS BOTÕES
======================================== */

async function enviarOpcao(id, texto = "") {
    let mensagemUsuario = null;

    try {
        if (botoes) {
            botoes.innerHTML = "";
        }

        // Mostra a escolha do usuário.
        mensagemUsuario = adicionarMensagem(
            texto || id,
            "user"
        );

        // Mostra o bot digitando.
        mostrarDigitando();

        const response = await fetch("/api/chat/responder", {
            method: "POST",

            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },

            body: JSON.stringify({
                ...obterDadosConversa(),
                opcao: id
            })
        });

        // O servidor respondeu: inicia a confirmação de recebimento.
        marcarComoRecebida(mensagemUsuario);

        await processarResposta(response);

    } catch (erro) {
        console.error("Erro ao enviar opção:", erro);

        removerDigitando();

        marcarComoRecebida(mensagemUsuario);

        adicionarMensagem(
            "Ocorreu um erro ao processar sua escolha. Tente novamente.",
            "bot"
        );
    }
}


/* ========================================
   ENVIAR MENSAGEM DIGITADA
======================================== */

async function enviarMensagem(texto) {
    if (!texto || !texto.trim()) return;

    texto = texto.trim();

    let mensagemUsuario = null;

    try {
        if (botoes) {
            botoes.innerHTML = "";
        }

        // Mostra a mensagem do usuário.
        mensagemUsuario = adicionarMensagem(texto, "user");

        // Mostra o bot digitando.
        mostrarDigitando();

        const response = await fetch("/api/chat/mensagem", {
            method: "POST",

            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },

            body: JSON.stringify({
                ...obterDadosConversa(),
                texto: texto
            })
        });

        // O servidor respondeu: confirma o recebimento.
        marcarComoRecebida(mensagemUsuario);

        await processarResposta(response);

    } catch (erro) {
        console.error("Erro ao enviar mensagem:", erro);

        removerDigitando();

        marcarComoRecebida(mensagemUsuario);

        adicionarMensagem(
            "Não foi possível enviar sua mensagem. Tente novamente.",
            "bot"
        );
    }
}


// =========================================================
// 4. MOSTRAR OPÇÕES E BOTÕES
// =========================================================

function mostrarOpcoes(opcoes = []) {
    if (!botoes) return;

    // Limpa os botões anteriores.
    botoes.innerHTML = "";

    // Identifica quando devemos mostrar cartões de profissionais.
    const etapaProfissional =
        etapaAtual === "agendamento_profissional";

    // Adiciona uma classe especial aos cartões.
    botoes.classList.toggle(
        "profissionais-container",
        etapaProfissional
    );

    // Não há opções para mostrar.
    if (!Array.isArray(opcoes) || opcoes.length === 0) {
        return;
    }

    opcoes.forEach((opcao) => {
        // Cria o botão.
        const botao = document.createElement("button");

        botao.type = "button";
        botao.classList.add("option-button", "chat-option");

        // Guarda o identificador da opção.
        botao.dataset.opcao = opcao.id;

        // Cartões especiais para profissionais.
        if (
            etapaProfissional &&
            opcao.imagem
        ) {
            botao.classList.add("profissional-card");

            const imagem = document.createElement("img");

            imagem.src = `/assets/${encodeURIComponent(opcao.imagem)}`;
            imagem.alt = opcao.texto || "Profissional";

            imagem.classList.add("profissional-imagem");

            // Evita imagens quebradas.
            imagem.onerror = () => {
                imagem.style.display = "none";
            };

            const nome = document.createElement("span");

            nome.textContent = opcao.texto || "Profissional";
            nome.classList.add("profissional-nome");

            botao.appendChild(imagem);
            botao.appendChild(nome);

        } else {
            // Botões normais.
            botao.textContent = opcao.texto || opcao.id;
        }

        // Executa a opção selecionada.
        botao.addEventListener("click", () => {
            enviarOpcao(opcao.id, opcao.texto);
        });

        botoes.appendChild(botao);
    });
}


// =========================================================
// 5. ATUALIZAR DADOS DO USUÁRIO NA TELA
// =========================================================

function atualizarUsuarioLogado() {
    // Atualiza o nome caso esses elementos existam no HTML.
    const elementosNome = [
        document.getElementById("user-name"),
        document.getElementById("usuario-nome"),
        document.getElementById("chat-user-name")
    ];

    elementosNome.forEach((elemento) => {
        if (elemento) {
            elemento.textContent = nomeUsuario || "Visitante";
        }
    });
}


// =========================================================
// 6. ATUALIZAR ESTADO COM A RESPOSTA DO BACKEND
// =========================================================

function atualizarEstado(dados) {
    if (!dados) return;

    // Atualiza a etapa da conversa.
    if (dados.etapa !== undefined) {
        etapaAtual = dados.etapa;
    }

    // Atualiza o ID do cliente.
    // É importante diferenciar null de undefined:
    // null significa limpar o login; undefined significa manter.
    if (dados.cliente_id !== undefined) {
        clienteId = dados.cliente_id;

        if (clienteId !== null) {
            localStorage.setItem(
                "agendaCorteClienteId",
                clienteId
            );
        } else {
            localStorage.removeItem("agendaCorteClienteId");
        }
    }

    // Atualiza o nome do usuário.
    if (dados.nome !== undefined) {
        nomeUsuario = dados.nome || "";

        if (nomeUsuario) {
            localStorage.setItem(
                "agendaCorteNome",
                nomeUsuario
            );
        } else {
            localStorage.removeItem("agendaCorteNome");
        }
    }

    // Atualiza a data de nascimento.
    if (dados.data_nascimento !== undefined) {
        dataNascimento = dados.data_nascimento;
    }

    // Atualiza o serviço escolhido.
    if (dados.servico_id !== undefined) {
        servicoId = dados.servico_id;
    }

    // Atualiza o profissional escolhido.
    if (dados.profissional_id !== undefined) {
        profissionalId = dados.profissional_id;
    }

    // Atualiza o tipo de cabelo.
    if (dados.tipo_cabelo !== undefined) {
        tipoCabelo = dados.tipo_cabelo;
    }

    // Atualiza a data do atendimento.
    if (dados.data_agendamento !== undefined) {
        dataAgendamento = dados.data_agendamento;
    }

    // Quando o backend informa logout, limpa os dados locais.
    if (dados.logout === true) {
        limparUsuario();
    }

    atualizarUsuarioLogado();
}


// =========================================================
// 7. LIMPAR DADOS DO USUÁRIO
// =========================================================

function limparUsuario() {
    // Limpa os dados de identificação.
    clienteId = null;
    nomeUsuario = "";
    dataNascimento = null;

    // Limpa os dados do agendamento atual.
    servicoId = null;
    profissionalId = null;
    tipoCabelo = null;
    dataAgendamento = null;

    // Remove os dados de login do navegador.
    localStorage.removeItem("agendaCorteClienteId");
    localStorage.removeItem("agendaCorteNome");

    atualizarUsuarioLogado();
}


// =========================================================
// 8. PREPARAR DADOS PARA O BACKEND
// =========================================================

function obterDadosConversa() {
    return {
        etapa: etapaAtual,
        cliente_id: clienteId,
        nome: nomeUsuario,
        data_nascimento: dataNascimento,
        servico_id: servicoId,
        profissional_id: profissionalId,
        tipo_cabelo: tipoCabelo,
        data_agendamento: dataAgendamento
    };
}


// =========================================================
// 9. PROCESSAR RESPOSTA DO SERVIDOR
// =========================================================



// =========================================================
// 10. INICIAR CONVERSA
// =========================================================

async function iniciarConversa() {
    try {
        // Limpa a interface antes de iniciar.
        if (mensagens) {
            mensagens.innerHTML = "";
        }

        if (botoes) {
            botoes.innerHTML = "";
        }

        // Busca a mensagem inicial do Flask.
        const response = await fetch("/api/chat/iniciar", {
            method: "GET",
            headers: {
                "Accept": "application/json"
            }
        });

        await processarResposta(response);

    } catch (erro) {
        console.error("Erro ao iniciar conversa:", erro);

        adicionarMensagem(
            "Não foi possível iniciar o atendimento. Atualize a página e tente novamente.",
            "bot"
        );
    }
}


// =========================================================
// 11. ENVIAR OPÇÃO DOS BOTÕES
// =========================================================



// =========================================================
// 12. ENVIAR MENSAGEM DIGITADA
// =========================================================



// =========================================================
// 13. EVENTO DO FORMULÁRIO
// =========================================================

if (formulario && campoTexto) {
    formulario.addEventListener("submit", async (evento) => {
        // Impede o formulário de recarregar a página.
        evento.preventDefault();

        const texto = campoTexto.value.trim();

        if (!texto) return;

        // Limpa o campo antes de enviar.
        campoTexto.value = "";

        await enviarMensagem(texto);

        campoTexto.focus();
    });
}


// =========================================================
// 14. INICIALIZAÇÃO DA PÁGINA
// =========================================================

document.addEventListener("DOMContentLoaded", () => {
    // Atualiza o nome salvo no navegador.
    atualizarUsuarioLogado();

    // Inicia o atendimento.
    iniciarConversa();
});
