# Setup — App Vida Wellington

---

## Pré-requisitos

- Python 3.11+ instalado → https://www.python.org/downloads/
- Conta no Telegram (baixar o app)
- Chave Anthropic (você já tem — para OCR de comprovantes)

---

## Passo 1 — Criar o Bot no Telegram

1. Abra o Telegram e procure por **@BotFather**
2. Mande `/newbot`
3. Escolha um nome: `App Vida Wellington`
4. Escolha um username (ex: `vida_wellington_bot`)
5. O BotFather vai te enviar um **token** — copie ele (parece: `123456789:AABBcc...`)

---

## Passo 2 — Instalar dependências

Abra o terminal na pasta do projeto:

```
cd "C:\Users\wellington\Projects\Dados pessoais"
pip install -r requirements.txt
```

---

## Passo 3 — Criar o arquivo .env

Copie o arquivo de exemplo:

```
copy .env.example .env
```

Edite o `.env` e preencha:

```
TELEGRAM_BOT_TOKEN=cole_o_token_do_botfather_aqui
TELEGRAM_CHAT_ID=deixa_vazio_por_enquanto
ANTHROPIC_API_KEY=sua_chave_aqui
APP_URL=http://localhost:5000
DB_PATH=data.db
```

---

## Passo 4 — Descobrir seu Chat ID

1. Rode o app pela primeira vez:
   ```
   python main.py
   ```
2. Abra o Telegram, procure pelo seu bot pelo username e mande `/start`
3. O bot vai responder mostrando: `Seu ID é: 123456789`
4. Copie esse número e coloque no `.env`:
   ```
   TELEGRAM_CHAT_ID=123456789
   ```
5. Reinicie o app: pare com `Ctrl+C` e rode `python main.py` de novo

---

## Passo 5 — Testar

- Acesse: **http://localhost:5000** — deve abrir o dashboard
- No Telegram, mande `/manha` pro bot e faça o check-in
- O dashboard deve atualizar com seus dados

---

## Passo 6 — Deploy no Railway (para acessar de qualquer lugar)

### 6.1 — Subir o código para o GitHub

1. Crie uma conta em github.com (se não tiver)
2. Crie um repositório privado chamado `app-vida`
3. No terminal:
   ```
   git init
   git add .
   git commit -m "App Vida v1"
   git remote add origin https://github.com/SEU_USER/app-vida.git
   git push -u origin main
   ```

### 6.2 — Configurar o Railway

1. Acesse **railway.app** e faça login com o GitHub
2. Clique em **New Project → Deploy from GitHub repo**
3. Selecione o repositório `app-vida`
4. Railway vai detectar o `Procfile` automaticamente
5. Vá em **Variables** e adicione as mesmas variáveis do `.env`:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `ANTHROPIC_API_KEY`
   - `APP_URL` (cole a URL que o Railway gerar, ex: `https://app-vida-production.up.railway.app`)

### 6.3 — Persistência de dados

O banco SQLite fica na memória do Railway e **pode ser apagado** ao redesenhar. Para não perder dados:

**Opção gratuita:** Use o comando `/backup` no bot toda semana — ele te manda um JSON com tudo.

**Opção permanente:** No Railway, adicione um **Volume** (US$ 0,25/GB/mês) e configure `DB_PATH=/data/data.db`.

---

## Comandos do bot

| Comando | O que faz |
|---|---|
| `/manha` | Check-in da manhã (7h30) |
| `/tarde` | Check-in da tarde (13h) |
| `/noite` | Check-in da noite (21h) |
| `/hoje` | Resumo do dia |
| `/streaks` | Ver dias sem fumar e sem beber |
| `/gastos` | Registrar gasto avulso |
| `/dashboard` | Link do painel |
| `/backup` | Exportar todos os dados em JSON |

---

## Problemas comuns

**Bot não responde:**
→ Verifique se `TELEGRAM_BOT_TOKEN` está correto no `.env`

**Dashboard não abre:**
→ Verifique se `python main.py` está rodando sem erros no terminal

**OCR não funciona:**
→ Verifique se `ANTHROPIC_API_KEY` está correto — OCR é opcional, você pode digitar o valor manualmente

**Dados sumindo no Railway:**
→ Configure um Volume ou use `/backup` regularmente
