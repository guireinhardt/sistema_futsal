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

## Deploy (Render + Neon)

O sistema detecta o banco via `DATABASE_URL` e sobe em produção via Gunicorn (`Procfile`, já configurado com múltiplos workers). Recomendação: **Neon** para o Postgres (free, persistente, não expira) + **Render** para o serviço web.

### 1. Banco de dados — Neon

1. Crie uma conta em [neon.tech](https://neon.tech) e um novo projeto.
2. Copie a *connection string* do dashboard (formato `postgresql://usuario:senha@ep-xxxx.neon.tech/nomedobanco?sslmode=require`) — é o valor de `DATABASE_URL`.
3. O Neon "suspende" o compute após alguns minutos sem uso e reconecta automaticamente na próxima query (leva menos de 1s). O `app.py` já está configurado com `pool_pre_ping` e `pool_recycle` para lidar com isso sem lançar erro 500.

### 2. Serviço web — Render

1. Suba o repositório para o GitHub (o `.env` fica de fora — está no `.gitignore`).
2. Crie um **Web Service** no Render apontando para o repositório. Ele detecta o `Procfile` automaticamente (`gunicorn --workers 2 --threads 4 --timeout 60 --bind 0.0.0.0:$PORT app:app`).
3. Configure as variáveis de ambiente do serviço:
   - `SECRET_KEY` — string aleatória forte (`python -c "import secrets; print(secrets.token_hex(32))"`)
   - `DEBUG=False`
   - `DATABASE_URL` — a connection string copiada do Neon
   - `ADMIN_USERNAME` — usuário do organizador
   - `ADMIN_PASSWORD_HASH` — hash gerado com `generate_password_hash` (nunca a senha em texto puro)
4. Em **Health Check Path**, configure `/healthz` — assim o Render reinicia o serviço automaticamente se ele travar, sem depender do banco (o endpoint não consulta o Postgres).
5. Rode as migrations contra o banco de produção uma vez (Shell do Render ou localmente com `DATABASE_URL` apontando pro Neon): `flask db upgrade`.
6. Acesse a aplicação e faça login em `/login` para cadastrar o primeiro campeonato.

### Limitações a saber

- **Plano free do Render "dorme"** após ~15 min sem acesso — o primeiro request depois disso demora ~30-60s. Se isso incomodar num dia de jogo, o plano pago (Starter, ~$7/mês) elimina o sleep. Um workaround gratuito é configurar um serviço externo (ex. [cron-job.org](https://cron-job.org), UptimeRobot) para pingar `/healthz` a cada 10 min — mantém o app "acordado", mas é um contorno, não garantia.
- **Uploads de logo são efêmeros:** logos enviados via formulário são salvos em `static/logos/` no disco local do servidor. Sem volume persistente, esse diretório é apagado a cada novo deploy/restart. Para logos permanentes, use os arquivos já versionados no repositório ou configure storage externo (S3, Cloudinary) antes de depender de uploads em produção.
- **Rate limit do login é por processo:** com 2 workers, o limite de 10 tentativas/min é contado separadamente por worker (na prática, até ~20/min no total). Suficiente para um app pequeno; para um limite mais rígido seria necessário um backend compartilhado (Redis) para o Flask-Limiter.

---

## Autor

**Guilherme Reinhardt**
[github.com/guireinhardt](https://github.com/guireinhardt)
