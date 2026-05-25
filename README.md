# Sistema de Gerenciamento de Campeonato de Futsal

Sistema web completo para organizar campeonatos de futsal — multi-campeonato, com fase de grupos, semi-finais geradas automaticamente, grande final e ranking de artilheiros.

![Tests](https://github.com/guireinhardt/sistema_futsal/actions/workflows/tests.yml/badge.svg)

---

## Funcionalidades

- **Multi-campeonato** — crie e alterne entre campeonatos distintos, cada um com seus times, jogadores e partidas isolados
- **Upload de logo** — logo do campeonato e dos times via upload (JPG/PNG, máx. 2MB), com preview antes de salvar
- **Fase de grupos** — cadastro de times, jogadores e partidas com registro de placar
- **Estatísticas por partida** — gols, assistências e defesas por jogador em cada jogo
- **Chaveamento automático** — semi-finais geradas com base na classificação (1º × 4º e 2º × 3º); final gerada com os vencedores
- **Artilheiros** — ranking dinâmico calculado a partir das estatísticas, sem campo manual
- **Detalhes de partida** — página dedicada por jogo com placar, vencedor e stats individuais
- **Testes automatizados** — 86 testes cobrindo modelos, serviços e rotas HTTP

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.11+ / Flask 3 |
| ORM | Flask-SQLAlchemy |
| Formulários | Flask-WTF + WTForms |
| Banco (dev) | SQLite |
| Banco (prod) | PostgreSQL |
| Frontend | HTML5 + Bootstrap 5 + CSS customizado |
| Testes | pytest + pytest-flask |
| Segurança | CSRF Protection, variáveis de ambiente |

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
# Edite o .env com sua SECRET_KEY

# 5. Rode a aplicação
python app.py
```

Acesse: `http://localhost:5000`

---

## Rodando os testes

```bash
python -m pytest
```

---

## Estrutura do projeto

```
sistema_futsal/
├── app.py                    # Rotas e configuração principal
├── models.py                 # Modelos: Tournament, Team, Player, Match, PlayerMatchStat
├── forms.py                  # Formulários WTForms
├── utils.py                  # Normalização de nomes de logo
├── services/
│   └── standingsService.py   # Classificação, semi-finais, final
├── templates/                # Templates Jinja2 (12 páginas)
├── static/
│   ├── css/                  # CSS por página
│   └── logos/                # Logos dos times e campeonatos
├── tests/                    # 86 testes automatizados
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

## Deploy

O sistema detecta o banco via variável `DATABASE_URL`. Para deploy no [Railway](https://railway.app) ou [Render](https://render.com):

1. Crie um serviço PostgreSQL na plataforma
2. Configure as variáveis de ambiente: `DATABASE_URL`, `SECRET_KEY`, `DEBUG=False`
3. A aplicação sobe automaticamente

---

## Autor

**Guilherme Reinhardt**
[github.com/guireinhardt](https://github.com/guireinhardt)
