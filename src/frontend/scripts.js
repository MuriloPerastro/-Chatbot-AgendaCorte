
const mensagens = document.getElementById("chat-messages");
const botoes = document.getElementById("chat-buttons");
const formulario = document.getElementById("chat-form");
const campoTexto = document.getElementById("user-input");

let etapaAtual = "inicio";
let servicoId = null;
let tipoCabelo = null;
let profissionalId = null;
// Dados temporários do cadastro.
let dadosCadastro = {
    nome: "",
    data_nascimento: ""
};

// Recupera o cliente salvo neste navegador.
let clienteId = localStorage.getItem("agendaCorteClienteId");


// ADICIONAR MENSAGEM AO CHAT.
function adicionarMensagem(texto, tipo) {
    const linha = document.createElement("div");

    linha.classList.add("message-row");
    linha.classList.add(
        tipo === "usuario" ? "user-row" : "bot-row"
    );

    const mensagem = document.createElement("div");

    mensagem.classList.add("message");
    mensagem.classList.add(
        tipo === "usuario" ? "user" : "bot"
    );

    // Adiciona o avatar nas mensagens do bot.
    if (tipo !== "usuario") {
        const avatar = document.createElement("img");

        avatar.src = "/assets/icone-app.jpg";
        avatar.alt = "AgendaCorte";
        avatar.classList.add("bot-avatar");

        linha.appendChild(avatar);
    }

    mensagem.textContent = texto;

    linha.appendChild(mensagem);
    mensagens.appendChild(linha);

    mensagens.scrollTop = mensagens.scrollHeight;
}


// MOSTRAR BOTÕES DE OPÇÕES.

function mostrarOpcoes(opcoes = []) {
    botoes.innerHTML = "";

    // Cartões especiais para escolha de profissional.
    if (etapaAtual === "agendamento_profissional") {
        botoes.classList.add("profissionais-container");

        opcoes.forEach(opcao => {
            const botao = document.createElement("button");
            botao.type = "button";
            botao.classList.add("profissional-card");

            const imagem = document.createElement("img");
            imagem.src = `/assets/${opcao.imagem}`;
            imagem.alt = opcao.texto;
            imagem.classList.add("profissional-imagem");

            imagem.onerror = () => {
                imagem.style.display = "none";
            };

            const nome = document.createElement("span");
            nome.textContent = opcao.texto;
            nome.classList.add("profissional-nome");

            botao.appendChild(imagem);
            botao.appendChild(nome);

            botao.addEventListener("click", () => {
                enviarOpcao(opcao.id, opcao.texto);
            });

            botoes.appendChild(botao);
        });

        return;
    }

    // Botões normais para as outras etapas.
    botoes.classList.remove("profissionais-container");

    opcoes.forEach(opcao => {
        const botao = document.createElement("button");

        botao.textContent = opcao.texto;
        botao.type = "button";

        botao.addEventListener("click", () => {
            enviarOpcao(opcao.id, opcao.texto);
        });

        botoes.appendChild(botao);
    });
}



// ATUALIZAR O CABEÇALHO DO USUÁRIO.
function atualizarUsuarioLogado() {
    const nomeElemento = document.getElementById("nome-usuario");
    const statusElemento = document.getElementById("status-usuario");

    const nome = localStorage.getItem("agendaCorteNome");

    // Evita erros caso os elementos não existam no HTML.
    if (!nomeElemento || !statusElemento) {
        return;
    }

    if (clienteId && nome) {
        nomeElemento.textContent = `Olá, ${nome}!`;
        statusElemento.textContent = "Cadastro reconhecido";
    } else {
        nomeElemento.textContent = "Olá, visitante!";
        statusElemento.textContent = "Não identificado";
    }
}


// ATUALIZAR ETAPA E DADOS DO CADASTRO.

function atualizarEstado(dados) {
    if (dados.etapa) {
        etapaAtual = dados.etapa;
    }

    if (dados.nome) {
        dadosCadastro.nome = dados.nome;

        localStorage.setItem(
            "agendaCorteNome",
            dados.nome
        );
    }

    if (dados.data_nascimento) {
        dadosCadastro.data_nascimento = dados.data_nascimento;
    }

    if (dados.cliente_id) {
        clienteId = dados.cliente_id;

        localStorage.setItem(
            "agendaCorteClienteId",
            clienteId
        );
    }

    // Guardar o serviço escolhido.
    if (dados.servico_id !== undefined) {
        servicoId = dados.servico_id;
    }

    // Guardar o tipo de cabelo escolhido.
    if (dados.tipo_cabelo !== undefined) {
        tipoCabelo = dados.tipo_cabelo;
    }

    if (dados.profissional_id !== undefined) {
    profissionalId = dados.profissional_id;
}

    atualizarUsuarioLogado();
}



// LIMPAR OS DADOS DO USUÁRIO ATUAL.
function limparUsuario() {
    clienteId = null;

    localStorage.removeItem("agendaCorteClienteId");
    localStorage.removeItem("agendaCorteNome");

    dadosCadastro = {
        nome: "",
        data_nascimento: ""
    };

    atualizarUsuarioLogado();
}


// INICIAR CONVERSA.
async function iniciarConversa() {
    try {
        const resposta = await fetch("/api/chat/iniciar");
        const dados = await resposta.json();

        if (!resposta.ok) {
            throw new Error(
                dados.erro || "Erro ao iniciar conversa."
            );
        }

        atualizarEstado(dados);

        adicionarMensagem(dados.mensagem, "bot");
        mostrarOpcoes(dados.opcoes);

    } catch (erro) {
        adicionarMensagem(
            "Não foi possível conectar ao servidor.",
            "bot"
        );

        console.error(erro);
    }
}


// ENVIAR OPÇÃO ESCOLHIDA.
async function enviarOpcao(id, texto) {
    adicionarMensagem(texto, "usuario");

    botoes.innerHTML = "";

    // Começar um cadastro novo.
    if (id === "cadastro") {
        limparUsuario();
    }

    // Atender outra pessoa.
    if (id === "trocar_usuario") {
        limparUsuario();
    }

    try {
        const resposta = await fetch("/api/chat/responder", {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                opcao: id,
                cliente_id: clienteId,
                servico_id: servicoId,
                tipo_cabelo: tipoCabelo,
                profissional_id: profissionalId
            })
        });

        const dados = await resposta.json();

        if (!resposta.ok) {
            throw new Error(
                dados.erro || "Erro ao enviar opção."
            );
        }

        atualizarEstado(dados);

        adicionarMensagem(dados.mensagem, "bot");
        mostrarOpcoes(dados.opcoes);

    } catch (erro) {
        adicionarMensagem(
            "Ocorreu um erro ao processar sua escolha.",
            "bot"
        );

        console.error(erro);
    }
}


// ENVIAR MENSAGEM DIGITADA.
async function enviarMensagem(texto) {
    adicionarMensagem(texto, "usuario");

    try {
        const resposta = await fetch("/api/chat/mensagem", {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                etapa: etapaAtual,
                texto: texto,

                // Dados necessários para concluir o cadastro.
                nome: dadosCadastro.nome,
                data_nascimento: dadosCadastro.data_nascimento
            })
        });

        const dados = await resposta.json();

        if (!resposta.ok) {
            throw new Error(
                dados.erro || "Erro ao enviar mensagem."
            );
        }

        atualizarEstado(dados);

        adicionarMensagem(dados.mensagem, "bot");
        mostrarOpcoes(dados.opcoes);

    } catch (erro) {
        adicionarMensagem(
            "Não foi possível processar sua mensagem.",
            "bot"
        );

        console.error(erro);
    }
}


// EVENTO DO FORMULÁRIO.
formulario.addEventListener("submit", evento => {
    evento.preventDefault();

    const texto = campoTexto.value.trim();

    if (!texto) {
        return;
    }

    campoTexto.value = "";

    enviarMensagem(texto);
});


// INICIAR QUANDO A PÁGINA CARREGAR.
document.addEventListener("DOMContentLoaded", () => {
    atualizarUsuarioLogado();
    iniciarConversa();
});
