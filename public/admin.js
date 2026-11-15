
/* =========================================
   ELEMENTOS DO HTML
========================================= */

const loginSection = document.getElementById("login-section");
const dashboardSection = document.getElementById("dashboard-section");

const loginForm = document.getElementById("login-form");
const passwordInput = document.getElementById("admin-password");
const loginButton = document.getElementById("login-button");
const loginError = document.getElementById("login-error");

const logoutButton = document.getElementById("logout-button");

const previousWeekButton = document.getElementById("previous-week");
const nextWeekButton = document.getElementById("next-week");
const currentWeekButton = document.getElementById("current-week");

const weekPeriod = document.getElementById("week-period");

const totalAppointments = document.getElementById("total-appointments");
const totalProfessionals = document.getElementById("total-professionals");

const appointmentsContainer = document.getElementById(
    "appointments-container"
);

const dashboardError = document.getElementById("dashboard-error");


/* =========================================
   ESTADO DO PAINEL
========================================= */

// Segunda-feira da semana atualmente selecionada.
let semanaAtual = obterSegundaFeira(new Date());

// Impede consultas simultâneas.
let carregandoAgenda = false;


/* =========================================
   REQUISIÇÕES AO BACKEND
========================================= */

async function requisicaoAPI(url, configuracoes = {}) {

    const resposta = await fetch(url, {
        ...configuracoes,

        // Mantém o cookie da sessão administrativa.
        credentials: "same-origin",

        headers: {
            "Content-Type": "application/json",
            ...configuracoes.headers
        }
    });

    // Tenta interpretar a resposta.
    const dados = await resposta.json().catch(() => ({}));

    if (!resposta.ok) {

        const erro = new Error(
            dados.erro || "Não foi possível realizar a operação."
        );

        erro.status = resposta.status;

        throw erro;
    }

    return dados;
}


/* =========================================
   CONTROLE DAS TELAS
========================================= */

function mostrarLogin() {

    loginSection.hidden = false;
    dashboardSection.hidden = true;

    passwordInput.value = "";
    loginError.textContent = "";

    passwordInput.focus();
}


function mostrarDashboard() {

    loginSection.hidden = true;
    dashboardSection.hidden = false;

    dashboardError.textContent = "";
}


/* =========================================
   LOGIN ADMINISTRATIVO
========================================= */

loginForm.addEventListener("submit", async (evento) => {

    evento.preventDefault();

    const senha = passwordInput.value.trim();

    if (!senha) {
        loginError.textContent = "Digite sua senha.";
        return;
    }

    loginButton.disabled = true;
    loginButton.textContent = "Verificando...";
    loginError.textContent = "";

    try {

        await requisicaoAPI("/api/admin/login", {
            method: "POST",

            body: JSON.stringify({
                senha: senha
            })
        });

        // Limpa o campo de senha.
        passwordInput.value = "";

        // Exibe o painel.
        mostrarDashboard();

        // Carrega a agenda.
        await carregarAgenda();

    } catch (erro) {

        loginError.textContent = erro.message;

    } finally {

        loginButton.disabled = false;
        loginButton.textContent = "Entrar";
    }

});


/* =========================================
   ENCERRAR SESSÃO
========================================= */

logoutButton.addEventListener("click", async () => {

    logoutButton.disabled = true;

    try {

        await requisicaoAPI("/api/admin/logout", {
            method: "POST"
        });

    } catch (erro) {

        console.error("Erro ao encerrar sessão:", erro);

    } finally {

        logoutButton.disabled = false;

        // Volta para o login independentemente da resposta.
        mostrarLogin();
    }

});


/* =========================================
   MANIPULAÇÃO DE DATAS
========================================= */

// Retorna a segunda-feira da semana de uma data.
function obterSegundaFeira(data) {

    const resultado = new Date(
        data.getFullYear(),
        data.getMonth(),
        data.getDate()
    );

    const dia = resultado.getDay();

    const diferenca = dia === 0 ? -6 : 1 - dia;

    resultado.setDate(resultado.getDate() + diferenca);

    return resultado;
}


// Converte uma data para YYYY-MM-DD sem alterar o fuso.
function dataParaISO(data) {

    const ano = data.getFullYear();

    const mes = String(
        data.getMonth() + 1
    ).padStart(2, "0");

    const dia = String(
        data.getDate()
    ).padStart(2, "0");

    return `${ano}-${mes}-${dia}`;
}


// Formata uma data recebida do backend.
function formatarData(dataTexto) {

    const [ano, mes, dia] = dataTexto.split("-").map(Number);

    const data = new Date(ano, mes - 1, dia);

    return data.toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric"
    });
}


// Calcula a data final da semana.
function obterFimSemana(inicio) {

    const fim = new Date(inicio);

    fim.setDate(fim.getDate() + 6);

    return fim;
}


// Atualiza o texto do período exibido.
function atualizarPeriodo() {

    const fim = obterFimSemana(semanaAtual);

    weekPeriod.textContent =
        `${formatarData(dataParaISO(semanaAtual))} até ` +
        `${formatarData(dataParaISO(fim))}`;
}


/* =========================================
   NAVEGAÇÃO ENTRE SEMANAS
========================================= */

previousWeekButton.addEventListener("click", () => {

    semanaAtual.setDate(semanaAtual.getDate() - 7);

    carregarAgenda();

});


nextWeekButton.addEventListener("click", () => {

    semanaAtual.setDate(semanaAtual.getDate() + 7);

    carregarAgenda();

});


currentWeekButton.addEventListener("click", () => {

    semanaAtual = obterSegundaFeira(new Date());

    carregarAgenda();

});


/* =========================================
   CARREGAR A AGENDA
========================================= */

async function carregarAgenda() {

    if (carregandoAgenda) return;

    carregandoAgenda = true;

    dashboardError.textContent = "";

    appointmentsContainer.innerHTML = `
        <p class="loading-message">
            Carregando agendamentos...
        </p>
    `;

    // Atualiza o período.
    atualizarPeriodo();

    // Desativa a navegação durante a consulta.
    previousWeekButton.disabled = true;
    nextWeekButton.disabled = true;
    currentWeekButton.disabled = true;

    try {

        const inicio = dataParaISO(semanaAtual);

        const dados = await requisicaoAPI(
            `/api/admin/agenda?inicio=${encodeURIComponent(inicio)}`
        );

        // Monta o painel com os dados recebidos.
        renderizarAgenda(dados);

    } catch (erro) {

        console.error("Erro ao carregar agenda:", erro);

        if (erro.status === 401) {

            // Sessão inexistente ou expirada.
            mostrarLogin();

        } else {

            dashboardError.textContent = erro.message;

            appointmentsContainer.innerHTML = `
                <p class="empty-message">
                    Não foi possível carregar os agendamentos.
                </p>
            `;
        }

    } finally {

        carregandoAgenda = false;

        previousWeekButton.disabled = false;
        nextWeekButton.disabled = false;
        currentWeekButton.disabled = false;
    }

}


/* =========================================
   SEGURANÇA: TRATAR TEXTOS HTML
========================================= */

function escaparHTML(valor) {

    return String(valor ?? "").replace(
        /[&<>"']/g,
        caractere => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        })[caractere]
    );

}


/* =========================================
   STATUS DOS AGENDAMENTOS
========================================= */

function obterStatus(status) {

    const original = String(
        status || "Não informado"
    );

    const normalizado = original
        .trim()
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "");

    if (normalizado === "cancelado" ||
        normalizado === "cancelada") {

        return {
            texto: "Cancelado",
            classe: "status-cancelled"
        };
    }

    if (normalizado === "pendente") {

        return {
            texto: "Pendente",
            classe: "status-pending"
        };
    }

    if (normalizado === "confirmado" ||
        normalizado === "confirmada") {

        return {
            texto: "Confirmado",
            classe: "status-confirmed"
        };
    }

    if (normalizado === "concluido" ||
        normalizado === "concluida" ||
        normalizado === "realizado" ||
        normalizado === "realizada") {

        return {
            texto: "Concluído",
            classe: "status-completed"
        };
    }

    return {
        texto: original,
        classe: "status-default"
    };

}


/* =========================================
   RENDERIZAR A AGENDA
========================================= */

function renderizarAgenda(dados) {

    const profissionais = dados.profissionais || [];

    let quantidadeAgendamentos = 0;

    // Conta todos os agendamentos retornados.
    profissionais.forEach(profissional => {

        quantidadeAgendamentos += (
            profissional.agendamentos || []
        ).length;

    });

    // Atualiza os indicadores.
    totalAppointments.textContent = quantidadeAgendamentos;

    totalProfessionals.textContent = profissionais.length;

    // Não existem profissionais cadastrados.
    if (profissionais.length === 0) {

        appointmentsContainer.innerHTML = `
            <p class="empty-message">
                Nenhum profissional encontrado.
            </p>
        `;

        return;
    }

    // Monta os cartões dos profissionais.
    appointmentsContainer.innerHTML = profissionais.map(
        profissional => {

            const agendamentos = (
                profissional.agendamentos || []
            ).slice().sort((a, b) => {

                const dataComparada = a.data.localeCompare(b.data);

                if (dataComparada !== 0) {
                    return dataComparada;
                }

                return a.horario_inicio.localeCompare(
                    b.horario_inicio
                );

            });

            return criarCartaoProfissional(
                profissional,
                agendamentos
            );

        }
    ).join("");

}


/* =========================================
   CARTÃO DO PROFISSIONAL
========================================= */

function criarCartaoProfissional(
    profissional,
    agendamentos
) {

    const nome = escaparHTML(profissional.profissional);

    const quantidade = agendamentos.length;

    // Sem agendamentos na semana.
    if (quantidade === 0) {

        return `
            <article class="professional-card">

                <header class="professional-header">

                    <h3>${nome}</h3>

                    <span class="professional-count">
                        0 agendamentos
                    </span>

                </header>

                <div class="professional-content">

                    <p class="empty-message">
                        Nenhum agendamento nesta semana.
                    </p>

                </div>

            </article>
        `;
    }

    // Agrupa os agendamentos por dia.
    const gruposPorDia = {};

    agendamentos.forEach(agendamento => {

        if (!gruposPorDia[agendamento.data]) {
            gruposPorDia[agendamento.data] = [];
        }

        gruposPorDia[agendamento.data].push(agendamento);

    });

    // Ordena as datas.
    const datas = Object.keys(gruposPorDia).sort();

    const gruposHTML = datas.map(data => {

        const atendimentos = gruposPorDia[data];

        return criarGrupoDia(data, atendimentos);

    }).join("");

    return `
        <article class="professional-card">

            <header class="professional-header">

                <h3>${nome}</h3>

                <span class="professional-count">
                    ${quantidade} ${
                        quantidade === 1
                            ? "agendamento"
                            : "agendamentos"
                    }
                </span>

            </header>

            <div class="professional-content">

                ${gruposHTML}

            </div>

        </article>
    `;

}


/* =========================================
   GRUPO DE UM DIA
========================================= */

function criarGrupoDia(data, agendamentos) {

    const dataFormatada = formatarData(data);

    const [ano, mes, dia] = data.split("-").map(Number);

    const dataLocal = new Date(ano, mes - 1, dia);

    const nomeDia = dataLocal.toLocaleDateString(
        "pt-BR",
        {
            weekday: "long"
        }
    );

    const nomeDiaFormatado =
        nomeDia.charAt(0).toUpperCase() + nomeDia.slice(1);

    const atendimentosHTML = agendamentos.map(
        criarItemAgendamento
    ).join("");

    return `
        <section class="day-group">

            <header class="day-header">

                <h4>${nomeDiaFormatado}</h4>

                <span class="day-date">
                    ${dataFormatada}
                </span>

            </header>

            ${atendimentosHTML}

        </section>
    `;

}


/* =========================================
   ITEM INDIVIDUAL DE AGENDAMENTO
========================================= */


function criarItemAgendamento(agendamento) {

    const id = escaparHTML(agendamento.id);
    const cliente = escaparHTML(agendamento.cliente);
    const servico = escaparHTML(agendamento.servico);

    const inicio = escaparHTML(agendamento.horario_inicio);
    const fim = escaparHTML(agendamento.horario_fim);

    const status = obterStatus(agendamento.status);

    const tipoCabelo = agendamento.tipo_cabelo
        ? ` · ${escaparHTML(agendamento.tipo_cabelo)}`
        : "";

    return `
        <article class="appointment-item">

            <div class="appointment-time">
                ${inicio}
                <span class="appointment-service">
                    até ${fim}
                </span>
            </div>

            <div class="appointment-info">

                <p class="appointment-client">
                    ${cliente}
                </p>

                <p class="appointment-service">
                    ${servico}${tipoCabelo}
                </p>

            </div>

            <div class="appointment-actions">

                <span class="appointment-status ${status.classe}">
                    ${escaparHTML(status.texto)}
                </span>

                <button
                    type="button"
                    class="delete-appointment-button"
                    data-agendamento-id="${id}"
                    aria-label="Excluir agendamento de ${cliente}"
                    title="Excluir agendamento"
                >
                    &#128465;
                </button>

            </div>

        </article>
    `;
}



/* =========================================
   VERIFICAR SESSÃO AO ABRIR A PÁGINA
========================================= */

async function verificarSessao() {

    try {

        // Tenta carregar a agenda.
        // Se a sessão existir, o backend autoriza.
        // Se não existir, retorna 401.

        mostrarDashboard();

        await carregarAgenda();

    } catch (erro) {

        console.error("Erro ao verificar sessão:", erro);

        mostrarLogin();

    }

}


/* =========================================
   INICIALIZAÇÃO
========================================= */

document.addEventListener("DOMContentLoaded", () => {

    verificarSessao();

});
/* =========================================
   EXCLUIR AGENDAMENTO
========================================= */

appointmentsContainer.addEventListener("click", async (evento) => {

    const botao = evento.target.closest(
        ".delete-appointment-button"
    );

    if (!botao) return;

    const agendamentoId = botao.dataset.agendamentoId;

    if (!agendamentoId) return;

    // Localiza o nome do cliente no cartão.
    const cartao = botao.closest(".appointment-item");

    const cliente = cartao.querySelector(
        ".appointment-client"
    )?.textContent || "este cliente";

    // Confirma antes de excluir.
    const confirmar = window.confirm(
        `Deseja realmente excluir o agendamento de ${cliente}?\n\n` +
        "Essa ação não poderá ser desfeita."
    );

    if (!confirmar) return;

    botao.disabled = true;
    botao.textContent = "...";

    try {

        await requisicaoAPI(
            `/api/admin/agendamento/${encodeURIComponent(agendamentoId)}`,
            {
                method: "DELETE"
            }
        );

        // Atualiza a agenda depois da exclusão.
        await carregarAgenda();

    } catch (erro) {

        console.error("Erro ao excluir agendamento:", erro);

        alert(erro.message);

        botao.disabled = false;
        botao.innerHTML = "&#128465;";

    }

});