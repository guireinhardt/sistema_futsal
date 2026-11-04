# Sistema de Gerenciamento de Campeonato de Futsal

Sistema web completo para organizar campeonatos de futsal — multi-campeonato, com fase de grupos, semi-finais geradas automaticamente, grande final e ranking de artilheiros.


---

## Funcionalidades

- **Multi-campeonato** — crie e alterne entre campeonatos distintos, cada um com seus times, jogadores e partidas isolados
- **Upload de logo** — logo do campeonato e dos times via upload (JPG/PNG, máx. 2MB), com preview antes de salvar
- **Fase de grupos** — cadastro de times, jogadores e partidas com registro de placar
- **Estatísticas por partida** — gols, assistências e defesas por jogador em cada jogo
- **Chaveamento automático** — semi-finais geradas com base na classificação (1º × 4º e 2º × 3º); final gerada com os vencedores
- **Artilheiros** — ranking dinâmico calculado a partir das estatísticas, sem campo manual
- **Detalhes de partida** — página dedicada por jogo com placar, vencedor e stats individuais
- **Área pública vs. administrativa** — qualquer visitante consulta classificação, jogos, jogadores e artilheiros; apenas o organizador autenticado cria/edita times, jogadores, placares e gera as fases
- **Confiabilidade em produção** — rate limit no login, health check dedicado, páginas de erro amigáveis, reconexão automática ao banco após inatividade
- **Testes automatizados** — 94 testes cobrindo modelos, serviços e rotas HTTP

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.11+ / Flask 3 |
| ORM | Flask-SQLAlchemy |
| Migrations | Flask-Migrate (Alembic) |
| Autenticação | Flask-Login (admin único) |
| Rate limiting | Flask-Limiter |
| Formulários | Flask-WTF + WTForms |
| Banco (dev) | SQLite |
| Banco (prod) | PostgreSQL |
| Servidor (prod) | Gunicorn |
| Frontend | HTML5 + Bootstrap 5 + CSS customizado |
| Testes | pytest + pytest-flask |
| Segurança | CSRF Protection, hash de senha (Werkzeug), variáveis de ambiente |

---

## Como rodar localmente

```bash
# 1. Clone o repositório
git clone https://github.com/guireinhardt/sistema_futsal.git
cd sistema_futsal

# 2. Crie e ative o ambiente virtual
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env: defina SECRET_KEY e gere o hash da senha do organizador
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('SUA_SENHA_AQUI'))"
# Cole o resultado em ADMIN_PASSWORD_HASH no .env

# 5. Crie as tabelas do banco (via migrations)
flask db upgrade

# 6. Rode a aplicação
python app.py
```

Acesse: `http://localhost:5000`

Para acessar a área administrativa (criar/editar times, jogadores, placares e gerar fases), vá em `/login` e entre com `ADMIN_USERNAME`/a senha que você definiu. As demais páginas (classificação, jogos, jogadores, artilheiros) são públicas.

---

## Rodando os testes

```bash
python -m pytest
```

---

## Estrutura do projeto

```
sistema_futsal/
├── app.py                    # Rotas, autenticação e configuração principal
├── models.py                 # Modelos: Tournament, Team, Player, Match, PlayerMatchStat
├── forms.py                  # Formulários WTForms (incl. LoginForm)
├── utils.py                  # Normalização de nomes de logo
├── services/
│   └── standingsService.py   # Classificação, semi-finais, final
├── migrations/                # Migrations do schema (Flask-Migrate/Alembic)
├── templates/                # Templates Jinja2 (13 páginas)
├── static/
│   ├── css/                  # CSS por página
│   └── logos/                # Logos dos times e campeonatos
├── tests/                    # 92 testes automatizados
├── Procfile                   # Comando de start em produção (gunicorn)
├── .env.example
└── requirements.txt
```

---

## Fluxo do campeonato

```
Criar campeonato → Cadastrar times e jogadores
        ↓
  Fase de grupos → Registrar placares e stats
        ↓
 [todos os jogos finalizados]
        ↓
  Semi-finais → geradas automaticamente (1º×4º, 2º×3º)
        ↓
 [semi-finais finalizadas]
        ↓
    Final → gerada com os vencedores
        ↓
      🥇 Campeão
```

---

## Deploy (Render + Neon + Cloudinary, tudo no plano free)

- **Neon:** banco PostgreSQL (persistente, não expira)
- **Cloudinary:** logos das seleções (o disco do Render é apagado a cada deploy)
- **Render:** o site

Faça na ordem abaixo: o Render precisa das credenciais dos outros dois já no primeiro deploy.

### 1. Banco de dados — Neon

1. Crie uma conta em [neon.tech](https://neon.tech) e um novo projeto (região mais próxima: São Paulo, se disponível).
2. Clique em **Connect** e copie a *connection string* (`postgresql://usuario:senha@ep-xxxx.neon.tech/neondb?sslmode=require`). Esse é o `DATABASE_URL`.

O Neon desliga o banco após 5 min sem uso e religa sozinho na próxima consulta. O `app.py` já trata isso (`pool_pre_ping`).

### 2. Logos — Cloudinary

1. Crie uma conta free em [cloudinary.com](https://cloudinary.com/users/register/free).
2. No dashboard, em **API Keys**, copie a **API environment variable** (`cloudinary://123456:abcdef@nome-da-conta`). Esse é o `CLOUDINARY_URL`.

### 3. Senha e chave secreta

**Senha do admin** (também serve quando você esquecer a senha):

```bash
python trocar_senha_admin.py
```

Ele gera uma senha forte aleatória e mostra uma única vez. Salve no seu gerenciador de senhas e confirme com `s`. Aí ele atualiza o `.env` local e mostra o hash para colar em `ADMIN_PASSWORD_HASH` no Render.

**Chave secreta do Flask:**

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Site — Render

1. Faça commit e push do código para o GitHub (o `.env` fica de fora, está no `.gitignore`).
2. Em [render.com](https://render.com), **New → Web Service**, conecte o repositório e preencha:
   - **Language:** Python 3 · **Instance Type:** Free
   - **Build Command:** `pip install -r requirements.txt && flask --app app db upgrade`
     (cria/atualiza as tabelas a cada deploy; o plano free não tem Shell)
   - **Start Command:** `gunicorn --workers 2 --threads 4 --timeout 60 --bind 0.0.0.0:$PORT app:app`
3. Em **Environment Variables**, antes de criar o serviço:

   | variável | valor |
   |---|---|
   | `PYTHON_VERSION` | `3.13.7` |
   | `DEBUG` | `False` |
   | `SECRET_KEY` | a chave gerada no passo 3 |
   | `ADMIN_USERNAME` | usuário do organizador (ex: `admin`) |
   | `ADMIN_PASSWORD_HASH` | o hash gerado no passo 3 (nunca a senha em texto puro) |
   | `DATABASE_URL` | a connection string do Neon |
   | `CLOUDINARY_URL` | a variável do Cloudinary |

4. Em **Advanced → Health Check Path**, coloque `/healthz`.
5. Crie o serviço e espere o deploy terminar (o log mostra `Running upgrade ... Initial schema`).
6. Abra a URL `https://<seu-servico>.onrender.com/healthz`, que deve mostrar `{"status": "ok"}`, e faça login em `/login` com a senha que você escolheu.

### 5. Carga das seleções e jogadores

Preencha `dados/selecoes.csv` (abre no Excel; separador `;`, uma linha por jogador):

| coluna | exemplo | observação |
|---|---|---|
| `selecao` | França | repita em cada jogador da seleção |
| `sigla` | FRA | até 4 letras |
| `logo` | franca.jpg ou https://res.cloudinary.com/... | arquivo em `static/logos/` ou link https (opcional) |
| `jogador` | Vini | deixe vazio para cadastrar só a seleção |
| `posicao` | fixo | goleiro, fixo, ala ou pivo |
| `camisa` | 6 | 1 a 99, sem repetir na mesma seleção |

Rode da sua máquina, definindo o banco e o Cloudinary **só no terminal** (não altere o `.env`, senão o ambiente local passa a gravar na homologação):

```powershell
# PowerShell — valem só enquanto este terminal estiver aberto
$env:DATABASE_URL = "postgresql://...neon.tech/neondb?sslmode=require"
$env:CLOUDINARY_URL = "cloudinary://..."

# confere a planilha sem gravar nada
python seed_selecoes.py dados/selecoes.csv --campeonato "Copa do Mundo Terça Féra" --edicao 2026 --simular
# grava
python seed_selecoes.py dados/selecoes.csv --campeonato "Copa do Mundo Terça Féra" --edicao 2026
```

Confira a linha `Banco:` no início da saída antes de gravar. O script mostra em qual banco vai gravar, cria o campeonato se não existir e pode ser rodado várias vezes: o que já existe é mantido, só entra o que falta. Se a planilha tiver qualquer erro, nada é gravado e todos os erros são listados com o número da linha. Logos sobem para o Cloudinary quando `CLOUDINARY_URL` está definido.

### Limitações a saber

- **Plano free do Render "dorme"** após ~15 min sem acesso — o primeiro request depois disso demora ~30-60s. Se isso incomodar num dia de jogo, o plano pago (Starter, ~$7/mês) elimina o sleep. Um workaround gratuito é configurar um serviço externo (ex. [cron-job.org](https://cron-job.org), UptimeRobot) para pingar `/healthz` a cada 10 min — mantém o app "acordado", mas é um contorno, não garantia.
- **Logos sem Cloudinary são efêmeros:** se `CLOUDINARY_URL` não estiver definido, os uploads vão para `static/logos/` no disco do servidor, que é apagado a cada deploy/restart no Render. Com `CLOUDINARY_URL` configurado, os logos ficam permanentes.
- **Rate limit do login é por processo:** com 2 workers, o limite de 10 tentativas/min é contado separadamente por worker (na prática, até ~20/min no total). Suficiente para um app pequeno; para um limite mais rígido seria necessário um backend compartilhado (Redis) para o Flask-Limiter.

---

## Autor

**Guilherme Reinhardt**
[github.com/guireinhardt](https://github.com/guireinhardt)
