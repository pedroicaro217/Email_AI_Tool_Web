# Email Marketer Web (Arquiteto de E-mails)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-black?logo=flask)
![Redis](https://img.shields.io/badge/Redis-red?logo=redis)
![License](https://img.shields.io/badge/License-MIT-green)

Uma aplicação web *self-hosted* (auto-hospedada) para automação de campanhas de e-mail marketing. Este projeto utiliza o Google Gemini (IA) para gerar conteúdo de e-mail dinâmico, branding e CTAs personalizados, e gerencia o envio em massa através de uma fila de tarefas assíncrona.

Este projeto é um portfólio que demonstra uma arquitetura web moderna, segura e robusta, desde a concepção até a implantação.

---

## 🚀 Funcionalidades

* **Geração de Conteúdo por IA:** Utiliza a API do Google Gemini para criar e-mails em HTML a partir de um simples prompt (tema).
* **Branding Dinâmico:** Injeta automaticamente o nome da empresa e a logo (com lógica condicional) no e-mail.
* **CTA Personalizado:** Permite definir uma URL de Call-to-Action (CTA) obrigatória para cada campanha.
* **Processamento Assíncrono:** Usa uma fila de tarefas (Redis + RQ) para enviar e-mails em segundo plano. O navegador não trava, mesmo com milhares de e-mails.
* **Painel de Admin Seguro:** Interface web para salvar credenciais (API Key, SMTP) de forma segura no banco de dados (fora do código).
* **Histórico de Campanhas:** Dashboard que mostra o status de todas as campanhas (Na Fila, Enviando, Concluído) e o status de *cada* destinatário (Enviado, Falhou).
* **Pré-visualização Real:** Renderiza o HTML gerado pela IA no navegador para aprovação *antes* do envio.
* **Manutenção de Estado:** Permite ao operador ajustar o prompt e gerar novas prévias sem perder os dados da campanha (como o CSV ou o assunto).

---

## 🏛️ Arquitetura

Este projeto é construído em uma arquitetura desacoplada, separando o servidor web do "trabalhador" (worker):

* **Backend:** Flask (Python)
* **Frontend:** HTML, CSS e Jinja2 (com templates herdados)
* **Banco de Dados:** SQLite (via Flask-SQLAlchemy) para salvar configurações, campanhas e destinatários.
* **Migrações de DB:** Flask-Migrate (Alembic)
* **Fila de Tarefas (Broker):** Redis
* **Trabalhador (Worker):** Redis Queue (RQ)
* **Geração de IA:** Google Gemini API
* **Ambiente de Desenvolvimento:** WSL2 (Windows Subsystem for Linux) para rodar o servidor Redis.

---

## 💡 Sobre o Processo de Desenvolvimento

Este projeto foi desenvolvido utilizando um processo ético e colaborativo de "pair programming" assistido por IA (Google Gemini), simulando uma parceria entre um desenvolvedor (humano) e um arquiteto de soluções (IA).

O Gemini atuou como um parceiro de codificação e arquiteto, sugerindo estruturas de dados, padrões de arquitetura (como a Fila de Tarefas com RQ/Redis) e blocos de código iniciais.

Como desenvolvedor principal, minha responsabilidade foi:
* **Definir os Requisitos:** Guiar o projeto, identificar *features* (como o prompt condicional) e apontar falhas de UX (como a perda de estado ao editar).
* **Validar a Arquitetura:** Analisar as soluções propostas pela IA, questioná-las e adaptá-las (como a mudança do `Worker` padrão para o `SimpleWorker` para compatibilidade com Windows).
* **Testar e Depurar:** Este **não** foi um processo de "copiar e colar". Cada linha de código sugerida pela IA foi rigorosamente validada, testada e depurada. A resolução de erros (como os `504` da API, erros de migração do DB e *constraints* de `UNIQUE`) foi um esforço conjunto de depuração e validação humana.
* **Concluir a programação** Realizar a versão final do codigo, juntando o bloco inicial, com o versão testada e depurada.

O resultado é um produto que reflete não apenas o poder da IA, mas a importância crucial do desenvolvedor em validar, testar e integrar o código de forma segura e robusta.

---

## ⚙️ Instalação e Configuração

Siga os passos abaixo para rodar o projeto localmente.

### 1. Pré-requisitos (Windows)

* [Git](https://git-scm.com/downloads)
* [Python 3.10+](https://www.python.org/downloads/)
* **WSL (Windows Subsystem for Linux):** O Redis (nossa fila) rodará no Linux. Siga [este guia oficial da Microsoft](https://learn.microsoft.com/pt-br/windows/wsl/install) para instalar o WSL e uma distribuição (ex: Ubuntu).

### 2. Instalação no Windows (com WSL)

1.  **Clone o repositório (no Windows):**
    ```bash
    git clone [https://github.com/pedroicaro217/Email_AI_Tool_Web.git](https://github.com/pedroicaro217/Email_AI_Tool_Web.git)
    cd Email_AI_Tool_Web
    ```

2.  **Crie e ative o ambiente virtual (no Windows):**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Instale as dependências Python (no Windows):**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Instale e inicie o Redis (via WSL):**
    * Abra um terminal separado para o **WSL (Ubuntu)**.
    * Execute os comandos de instalação do Redis (apenas na primeira vez):
        ```bash
        curl -fsSL [https://packages.redis.io/gpg](https://packages.redis.io/gpg) | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
        echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] [https://packages.redis.io/deb](https://packages.redis.io/deb) $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
        sudo apt-get update
        sudo apt-get install redis
        ```
    * Após a instalação, inicie o serviço Redis. **Este terminal WSL deve ficar aberto.**
        ```bash
        sudo service redis-server start
        ```
    * Teste se funcionou (no WSL): `redis-cli ping` (Deve responder `PONG`).

---

### 3. Instalação no Linux (Nativo)

Se você estiver em um servidor ou desktop Linux.

1.  **Instale as dependências do sistema:**
    ```bash
    sudo apt-get update
    sudo apt-get install git python3-venv redis-server -y
    ```

2.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/pedroicaro217/Email_AI_Tool_Web.git](https://github.com/pedroicaro217/Email_AI_Tool_Web.git)
    cd Email_AI_Tool_Web
    ```

3.  **Crie e ative o ambiente virtual:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

4.  **Instale as dependências Python:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Verifique se o Redis está rodando:**
    ```bash
    sudo service redis-server status
    ```
    (O serviço `redis-server` geralmente inicia automaticamente após a instalação no Linux).

---

### 4. Configuração (Ambos os Sistemas)

Após a instalação, configure a aplicação:

1.  **Crie o arquivo `.env`:**
    * Copie o template de exemplo:
        ```bash
        # Windows
        copy .env.example .env
        # Linux
        cp .env.example .env
        ```
    * Edite o arquivo `.env` e adicione sua `SECRET_KEY` aleatória e o `REDIS_URL` (o padrão `redis://localhost:6379` deve funcionar).

2.  **Crie o Banco de Dados:**
    * Com o `venv` ativo, execute as migrações do Flask:
        ```bash
        flask db upgrade
        ```
    * *(Se for a primeira vez, pode ser necessário rodar `flask db init` e `flask db migrate` antes).*
    * Isso criará o arquivo `instance/database.db`.

3.  **Configure as Credenciais (Via Web):**
    * Inicie o servidor Flask (veja "Como Rodar" abaixo).
    * Abra o navegador e vá para `http://127.0.0.1:5000`.
    * Você será redirecionado para o "Histórico". Clique em **"🔧 Configurações"** no menu.
    * Preencha **todas** as credenciais (API Key do Gemini, dados do SMTP e o Nome da Empresa) e clique em "Salvar".

---

## 🚀 Como Rodar

Para operar a aplicação, você precisa de **3 terminais** rodando simultaneamente (no Windows: 1 WSL e 2 VSCode/CMD).

1.  **Terminal 1: O Servidor Redis (A Fila)**
    * Garanta que o serviço do Redis esteja rodando.
    * (No Windows: Mantenha o terminal WSL aberto com `sudo service redis-server start`.)
    * (No Linux: `sudo service redis-server status` para garantir que está no ar.)

2.  **Terminal 2: O Servidor Web (Flask)**
    * Abra um terminal na raiz do projeto.
    * Ative o venv: `.\venv\Scripts\activate` (Windows) ou `source venv/bin/activate` (Linux).
    * Inicie o Flask:
        ```bash
        python run.py
        ```

3.  **Terminal 3: O Trabalhador (Worker)**
    * Abra um **novo** terminal na raiz do projeto.
    * Ative o venv: `.\venv\Scripts\activate` (Windows) ou `source venv/bin/activate` (Linux).
    * Inicie o worker do RQ (ele ficará "ouvindo"):
        ```bash
        python worker.py
        ```

Com os 3 terminais no ar, acesse `http://127.0.0.1:5000` no seu navegador para usar a aplicação.