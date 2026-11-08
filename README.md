# 💈 AgendaCorte - Chatbot de Agendamento Inteligente

## 📖 Sobre o Projeto
O **AgendaCorte** é um chatbot inteligente projetado para barbearias e salões de beleza, automatizando o atendimento aos clientes. O sistema facilita o agendamento de horários, escolha de profissionais, consulta de serviços (corte, barba, tratamentos químicos) e envio de lembretes, ajudando a desafogar a recepção e eliminando falhas de marcação.

---

## 🛠️ Tecnologias e Arquitetura
O projeto utiliza uma stack moderna voltada para agilidade, escalabilidade e colaboração em nuvem:
* **Linguagem:** Python 3.x
* **Banco de Dados:** PostgreSQL hospedado no **Supabase**
* **Ambiente de Desenvolvimento:** GitHub Codespaces / VS Code
* **Bibliotecas Principais:** `supabase-py`, `python-dotenv`

---

## 🗄️ Estrutura do Banco de Dados
O sistema conta com as seguintes tabelas principais modeladas no Supabase:
* `clientes`: Cadastro dos usuários/clientes do salão.
* `profissionais`: Cadastro dos barbeiros/profissionais (incluindo o campo descritivo livre `descricao` para biografia/especialidades).
* `servicos`: Catálogo de serviços oferecidos.
* `profissional_servicos`: Tabela associativa (relação N:N) entre profissionais e os serviços que cada um realiza.
* `agendamentos`: Registro das marcações com restrições de horário para evitar conflitos (`unique_profissional_horario`) e validação de carimbo de data/hora (`criado_em`).

---

## 📂 Estrutura de Pastas
Para manter o projeto organizado e modular, o código-fonte está estruturado da seguinte forma:

```text
-Chatbot-AgendaCorte/
│
├── .vscode/
│   └── settings.json         # Configuração automática do ambiente e do .env
│
├── src/                      # Código-fonte principal da aplicação
│   ├── __init__.py           # Torna a pasta um pacote Python
│   ├── database.py           # Conexão centralizada com o Supabase
│   ├── models/               # Estruturas de dados e entidades
│   ├── services/             # Lógica de negócio (profissionais, agendamentos, etc.)
│   └── bot/                  # Lógica do chatbot e fluxos de conversação
│
├── tests/                    # Ficheiros de teste automatizados/manuais
│   └── test_conexao.py       # Script de validação da conexão com o Supabase
│
├── .env                      # Variáveis de ambiente (ignorado pelo Git por segurança)
├── .gitignore                # Ficheiros e pastas ignorados pelo controle de versão
├── README.md                 # Documentação oficial do projeto
└── requirements.txt          # Dependências do Python
```

---

## 🚀 Como Executar o Projeto no Codespaces

1. **Abra o repositório no GitHub Codespaces** (ou clone localmente).
2. **Configure o arquivo de variáveis de ambiente:**
   Na raiz do projeto, crie um arquivo chamado `.env` baseado nas suas credenciais do Supabase:
   ```env
   SUPABASE_URL='https://wemrbvpmjfbjddwidsoz.supabase.co'
   SUPABASE_KEY='sb_publishable_ET3k4izjjRB1CS4bLhZXWw_-Er5SkFq'
   ```