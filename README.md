# 🗺️ MapsScraper SaaS - API & Engine de Extração de Leads

Uma solução completa de **Micro-SaaS / API REST** construída em Python para extração dinâmica, mapeamento e estruturação de dados de estabelecimentos e empresas no **Google Maps**.

O projeto evoluiu de um script local em Playwright para uma arquitetura assíncrona, orientada a microserviços, com suporte a **autenticação por API Key**, **gestão de créditos por usuário**, **banco de dados SQLite/PostgreSQL** e **execução de tarefas em segundo plano**.

---

## 📐 Arquitetura da Solução
┌─────────────────────────────────────────────────────────────┐
│                     Cliente / Frontend                      │
│        (Requisição HTTP com cabeçalho X-API-Key)            │
└──────────────────────────────┬──────────────────────────────┘
│
┌──────────────────────────────▼──────────────────────────────┐
│                  FastAPI (API Gateway)                      │
│  - Validação de API Key & Créditos                          │
│  - Swagger / OpenAPI Documentation                          │
└──────────────┬───────────────────────────────┬──────────────┘
│                               │
┌──────────────▼──────────────┐ ┌──────────────▼──────────────┐
│    Banco de Dados (SQLite)   │ │  Background Task (Async)    │
│   - Tabela de Usuários      │ │  - Engine em Playwright     │
│   - Tabela de Jobs/Histórico│ │  - Parser dinâmico de blocos│
└─────────────────────────────┘ └──────────────┬──────────────┘
│
┌──────────────▼──────────────┐
│      Exportação Final       │
│      (Gerador de CSV)       │
└─────────────────────────────┘


---

## ✨ Principais Funcionalidades

- **Raspagem Dinâmica & Resiliente:** Coleta automática de telefones, websites, endereços e faixas de preço usando seleção inteligente de seletores no Google Maps.
- **Processamento Assíncrono (Background Tasks):** Requisições de extração não travam a API. O cliente recebe um `job_id` para consultar o progresso.
- **Sistema de Autenticação via API Key:** Acesso seguro às rotas da API passando o cabeçalho `X-API-Key: sk_live_...`.
- **Gestão Integrada de Créditos:** Dedução automática do saldo de créditos do usuário com base no número de resultados solicitados.
- **Persistência de Dados (ORM):** Utilização do **SQLAlchemy** para gerenciar contas de usuários e histórico de extrações.
- **Exportação Pronta para Vendas:** Dados salvos e formatados em arquivos `.csv` (com suporte nativo a acentuação e Excel via UTF-8-SIG).

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.10+
- **Web Framework:** [FastAPI](https://fastapi.tiangolo.com/)
- **Servidor ASGI:** Uvicorn
- **Automação Web:** [Playwright](https://playwright.dev/python/) (Async Engine)
- **Análise e Tratamento de Dados:** Pandas & Regex
- **Banco de Dados & ORM:** SQLite / SQLAlchemy
- **Validação de Dados:** Pydantic

---

## 🚀 Como Executar o Projeto

### Pré-requisitos

- Python 3.10 ou superior instalado
- Navegadores do Playwright instalados

### 1. Clonar o repositório e preparar o ambiente

# Clonar o repositório
git clone [https://github.com/seu-usuario/maps-scraper-saas.git](https://github.com/seu-usuario/maps-scraper-saas.git)
cd maps-scraper-saas

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # No Windows: venv\\Scripts\\activate

# Instalar dependências
pip install fastapi uvicorn playwright pandas sqlalchemy pydantic

# Instalar os navegadores do Playwright
playwright install chromium
2. Iniciar a API
Bash

python app.py
A API estará rodando em http://localhost:8000.

📖 Documentação da API
Acesse a documentação interativa OpenAPI (Swagger UI) navegando para:
👉 http://localhost:8000/docs

Fluxo de Uso Comercial
1️⃣ Criar um Usuário e Obter a API Key
Endpoint: POST /admin/usuarios

JSON

// Request Body
{
  "nome": "Empresa Cliente",
  "email": "contato@empresa.com"
}
Resposta: Retorna a api_key no formato sk_live_... e o saldo inicial de 100 créditos.

2️⃣ Autenticação
Insira no cabeçalho HTTP de todas as requisições privadas:

HTTP

X-API-Key: sk_live_sua_chave_aqui
3️⃣ Iniciar uma Extração de Leads
Endpoint: POST /v1/scrape

JSON

// Request Body
{
  "termo": "Restaurantes",
  "max_resultados": 20
}
Resposta: Retorna o job_id para monitoramento.

4️⃣ Checar Status e Baixar o CSV
Status: GET /v1/jobs/{job_id}
Download do CSV: GET /v1/jobs/{job_id}/download
🛣️ Roadmap / Próximos Passos (To-Do)
[x] Engine de raspagem dinâmica e rolagem do feed do Google Maps.
[x] Estruturação da API assíncrona com FastAPI.
[x] Sistema de autenticação por API Key e créditos no banco de dados.
[ ] Painel Dashboard Web (Frontend em Streamlit ou Next.js).
[ ] Integração com Gateway de Pagamentos (Asaas/Stripe) para recarga automática de créditos via PIX/Cartão.
[ ] Conteinerização completa da aplicação com Docker & Docker Compose.
[ ] Deploy na nuvem (AWS / Render / Railway).
📝 Licença
Este projeto está sob a licença MIT. Sinta-se à vontade para utilizar, modificar e expandir!


Após executar esse comando no terminal:
1. O arquivo `README.md` aparecerá na barra lateral esquerda do seu VS Code / Codespaces.
2. Se quiser baixá-lo localmente, basta clicar nele com o **botão direito** no painel d
