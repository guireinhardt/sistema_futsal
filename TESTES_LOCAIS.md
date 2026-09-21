# Guia de Testes Locais — Sistema Futsal

Antes de fazer deploy, execute estes testes para validar que tudo está funcionando.

---

## 1. Setup Local

```bash
# Dentro do projeto
python -m venv venv
venv\Scripts\activate         # Windows
source venv/bin/activate      # Linux/Mac

pip install -r requirements.txt

# Criar banco limpo
rm -f instance/football.db

# Configurar .env (já existe, abra e verifique)
cat .env
# Deve ter:
# SECRET_KEY=...
# DEBUG=False
# DATABASE_URL=sqlite:///football.db
# ADMIN_USERNAME=admin
# ADMIN_PASSWORD_HASH=scrypt:32768:8:1$...
```

---

## 2. Testes Automatizados (94 testes)

```bash
python -m pytest -v
```

✅ **Esperado:** `94 passed` (nenhuma falha)

Se algum test falhar, é um bug — não prossiga pro deploy.

---

## 3. Iniciar o Servidor Local

```bash
python app.py
```

Você deve ver:
```
WARNING: This is a development server. Do not use it in the production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

Abra o navegador em **http://127.0.0.1:5000**

---

## 4. Testes Manuais

### 4.1. Página Inicial (Pública)

- [ ] Homepage carrega sem erro (título "Sistema de Campeonato")
- [ ] Link "Login do organizador" está visível no topo
- [ ] Botões "Tabela de Classificação", "Lista de Jogadores", "Artilheiros", "Lista de Jogos" estão visíveis
- [ ] Botões "Adicionar Time", "Adicionar Jogador", "Adicionar Partida" **NÃO** estão visíveis (ainda sem login)

### 4.2. Tentar Acessar Rota Protegida (Sem Login)

- [ ] Clique em "Adicionar Time" (ou acesse diretamente `http://127.0.0.1:5000/add_team`)
- [ ] **Esperado:** redirect automático para `/login?next=%2Fadd_team`

### 4.3. Login

- [ ] Vá para `http://127.0.0.1:5000/login`
- [ ] Tente login com usuário errado (ex: `user / pass123`)
  - [ ] **Esperado:** mensagem "Usuário ou senha inválidos."
- [ ] Tente login com senha errada (ex: `admin / senhaErrada`)
  - [ ] **Esperado:** mensagem "Usuário ou senha inválidos."
- [ ] Login correto: `admin / pHe1uLN0GMGdn4hp` (a senha que está no seu `.env`)
  - [ ] **Esperado:** redirect para homepage com mensagem "Login realizado com sucesso!"
  - [ ] **Esperado:** agora os botões "Adicionar Time", "Adicionar Jogador", etc. aparecem
  - [ ] **Esperado:** link no topo muda para "Sair da área administrativa"

### 4.4. Fluxo Completo Autenticado

#### Criar Campeonato
- [ ] Clique em "Campeonatos" (ou acesse `/tournament/new`)
- [ ] Preencha:
  - Nome: "Teste Local 2026"
  - Edição: "Local"
  - Logo: (deixe em branco, opcional)
- [ ] Clique "Criar campeonato"
- [ ] **Esperado:** mensagem "Campeonato criado e selecionado!"
- [ ] Volta para homepage e exibe "Teste Local 2026" no topo

#### Adicionar Times
- [ ] Clique em "Adicionar Time"
- [ ] Crie 2 times (ex: "Time A", "Time B")
- [ ] **Esperado:** cada um exibe mensagem "Time adicionado com sucesso!"

#### Adicionar Jogadores
- [ ] Clique em "Adicionar Jogador"
- [ ] Para Time A, crie 3 jogadores:
  - João Silva, Ala, camisa 10
  - Pedro Santos, Fixo, camisa 5
  - Carlos Gol, Goleiro, camisa 1
- [ ] Para Time B, crie 2 jogadores:
  - Marco Zeta, Ala, camisa 11
  - Ana Defesa, Fixo, camisa 6
- [ ] Clique em "Jogadores" — veja os times com seus jogadores listados

#### Adicionar Partidas
- [ ] Clique em "Adicionar Partida"
- [ ] Crie uma partida:
  - Time A vs Time B
  - Fase: "Fase de Grupos"
- [ ] **Esperado:** "Partida adicionada!" e aparece na "Lista de Jogos"

#### Editar Placar
- [ ] Na "Lista de Jogos", clique "Editar" na partida criada
- [ ] Preencha:
  - Score A: 3
  - Score B: 1
  - Goals Time A (João): 2, (Pedro): 1
  - Goals Time B (Marco): 1
- [ ] Clique "Salvar"
- [ ] **Esperado:** "Partida e estatísticas salvas!"
- [ ] Volte para "Lista de Jogos" — veja o placar "3 vs 1"
- [ ] Clique no placar para ver detalhes da partida

#### Classificação
- [ ] Clique em "Tabela de Classificação"
- [ ] **Esperado:** Time A com 3 pontos (1 vitória), Time B com 0 pontos (1 derrota)
- [ ] Botão "Editar" no placar **deve estar visível** (ainda está autenticado)

#### Artilheiros
- [ ] Clique em "Artilheiros" (ou "Top Scorers")
- [ ] **Esperado:** João Silva em 1º com 2 gols, Pedro em 2º com 1 gol, Marco em 3º com 1 gol

### 4.5. Logout e Verificar Proteção

- [ ] Clique em "Sair da área administrativa"
- [ ] **Esperado:** volta para homepage com mensagem "Você saiu da área administrativa."
- [ ] **Esperado:** botões administrativos desaparecem, link muda para "Login do organizador"
- [ ] Tente acessar `/add_team` diretamente
- [ ] **Esperado:** redirect para `/login?next=%2Fadd_team`

### 4.6. Teste de Health Check

```bash
# Em outro terminal (ou use curl online)
curl http://127.0.0.1:5000/healthz
```

✅ **Esperado:** `{"status":"ok"}` com HTTP 200

### 4.7. Teste de Página 404

- [ ] Acesse `http://127.0.0.1:5000/pagina-inexistente`
- [ ] **Esperado:** página amigável "404 — Essa página não existe ou foi movida"
- [ ] **Esperado:** botão "Voltar para o início"

### 4.8. Rate Limit (Bonus)

```bash
# Em outro terminal, rode um script que tenta login 15 vezes em 1 minuto
for i in {1..15}; do
  curl -X POST http://127.0.0.1:5000/login \
    --data "username=admin&password=teste" \
    -o /dev/null -s -w "Tentativa $i -> %{http_code}\n"
  sleep 2
done
```

✅ **Esperado:** 
- Primeiras 10 tentativas: HTTP 200
- Tentativas 11-15: HTTP 429 (Too Many Requests)

---

## 5. Checklist Antes do Deploy

- [ ] Todos os 94 testes passam (`pytest -q` sem erros)
- [ ] Servidor sobe sem erros (`python app.py`)
- [ ] Página inicial carrega
- [ ] Login/logout funciona
- [ ] Fluxo completo (criar campeonato → times → jogadores → partida → placar → classificação) funciona
- [ ] Páginas públicas (classificação, jogadores, artilheiros) funcionam sem login
- [ ] Páginas administrativas redirecionam para login sem autenticação
- [ ] Health check `/healthz` responde com 200
- [ ] Página 404 é amigável
- [ ] Nenhuma senha ou chave sensível aparece em logs ou mensagens de erro

---

## 6. Problemas Comuns

### ImportError ou módulo não encontrado
```bash
pip install -r requirements.txt --upgrade
```

### Banco corrompido ou com schema antigo
```bash
rm -f instance/football.db
flask db upgrade
```

### Porta 5000 já está em uso
```bash
# Mude a porta no comando:
python -c "from app import app; app.run(port=5001)"
```

### ADMIN_PASSWORD_HASH não configurado (erro ao iniciar)
```bash
# Se estiver em DEBUG=True, pode ignorar
# Senão, gere um hash:
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('sua-senha-aqui'))"

# E atualize o .env:
ADMIN_PASSWORD_HASH=scrypt:32768:8:1$...
```

---

## 7. Pronto para Deploy?

Se chegou aqui e tudo passou:

✅ **Código está pronto**

Próximos passos:
1. Criar conta Neon (banco Postgres)
2. Criar conta Render (serviço web)
3. Conectar repositório ao Render
4. Configurar variáveis de ambiente
5. Rodar migrations: `flask db upgrade`

Qualquer dúvida ou erro durante os testes, avise antes de fazer deploy!
