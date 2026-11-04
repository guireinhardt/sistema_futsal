"""Carga de seleções e jogadores a partir de uma planilha CSV.

Uso:
    python seed_selecoes.py dados/selecoes.csv --campeonato "Copa do Mundo Terça Féra" --edicao 2026
    python seed_selecoes.py dados/selecoes.csv --campeonato "..." --edicao 2026 --simular
    python seed_selecoes.py dados/selecoes.csv --campeonato "..." --edicao 2026 --resetar

Grava no banco definido em DATABASE_URL (.env). Pode rodar mais de uma vez:
seleções e jogadores que já existem são mantidos, só o que falta é inserido.
Com --resetar, apaga antes os times, jogadores e jogos desse campeonato.
"""

import argparse
import csv
import os
import sys

from sqlalchemy import or_, select
from unidecode import unidecode

from app import app, cloudinary_url
from models import db, Tournament, Team, Player, Match, PlayerMatchStat

POSICOES = {"goleiro", "fixo", "ala", "pivo"}
COLUNAS = {"selecao", "sigla", "logo", "jogador", "posicao", "camisa"}
LOGOS_DIR = os.path.join(app.root_path, "static", "logos")


def ler_planilha(caminho):
    # "CSV UTF-8" do Excel é utf-8-sig; o "CSV (separado por vírgulas)" é cp1252.
    try:
        with open(caminho, encoding="utf-8-sig", newline="") as f:
            texto = f.read()
    except UnicodeDecodeError:
        with open(caminho, encoding="cp1252", newline="") as f:
            texto = f.read()

    dialeto = csv.Sniffer().sniff(texto[:2048], delimiters=";,")
    leitor = csv.DictReader(texto.splitlines(), dialect=dialeto)
    faltando = COLUNAS - {c.strip().lower() for c in leitor.fieldnames or []}
    if faltando:
        sys.exit(f"Colunas ausentes na planilha: {', '.join(sorted(faltando))}")
    return [
        {k.strip().lower(): (v or "").strip() for k, v in linha.items() if k}
        for linha in leitor
    ]


def validar(linhas):
    """Retorna (selecoes, jogadores, erros) já normalizados."""
    selecoes, jogadores, erros = {}, [], []

    for n, linha in enumerate(linhas, start=2):  # linha 1 é o cabeçalho
        nome = linha["selecao"]
        if not nome:
            if any(linha.values()):
                erros.append(f"Linha {n}: coluna 'selecao' vazia.")
            continue

        sigla = linha["sigla"].upper()
        if len(sigla) > 4:
            erros.append(f"Linha {n}: sigla '{sigla}' tem mais de 4 letras.")
        logo = linha["logo"]
        if logo.startswith("http://"):
            erros.append(f"Linha {n}: use o link https:// do logo.")
        elif logo and not logo.startswith("https://") and not os.path.isfile(
            os.path.join(LOGOS_DIR, logo)
        ):
            erros.append(f"Linha {n}: logo '{logo}' não encontrado em static/logos/.")

        sel = selecoes.setdefault(nome, {"sigla": "", "logo": ""})
        sel["sigla"] = sel["sigla"] or sigla
        sel["logo"] = sel["logo"] or logo

        if not linha["jogador"]:
            continue
        quem = f"Linha {n} ({linha['jogador']})"
        posicao = unidecode(linha["posicao"]).lower()
        if not posicao:
            erros.append(f"{quem}: posição em branco (use {', '.join(sorted(POSICOES))}).")
        elif posicao not in POSICOES:
            erros.append(
                f"{quem}: posição '{linha['posicao']}' inválida "
                f"(use {', '.join(sorted(POSICOES))})."
            )
        camisa = None
        if not linha["camisa"]:
            erros.append(f"{quem}: camisa em branco (número de 1 a 99).")
        else:
            try:
                camisa = int(linha["camisa"])
                if not 1 <= camisa <= 99:
                    raise ValueError
            except ValueError:
                erros.append(f"{quem}: camisa '{linha['camisa']}' deve ser um número de 1 a 99.")
                camisa = None

        jogadores.append(
            {"linha": n, "selecao": nome, "nome": linha["jogador"],
             "posicao": posicao, "camisa": camisa}
        )

    for nome, sel in selecoes.items():
        if not sel["sigla"]:
            erros.append(f"Seleção '{nome}' está sem sigla.")

    vistos = {}
    for j in jogadores:
        chave = (j["selecao"], j["camisa"])
        if j["camisa"] is not None and chave in vistos:
            erros.append(
                f"Linha {j['linha']}: camisa {j['camisa']} repetida em {j['selecao']} "
                f"(já usada na linha {vistos[chave]})."
            )
        vistos.setdefault(chave, j["linha"])

    return selecoes, jogadores, erros


def resolver_logo(arquivo, nome_selecao):
    """Link já hospedado é usado direto; arquivo local sobe pro Cloudinary se configurado."""
    if arquivo.startswith("https://") or not cloudinary_url:
        return arquivo
    import cloudinary.uploader

    public_id = unidecode(nome_selecao.strip().lower().replace(" ", "_"))
    resultado = cloudinary.uploader.upload(
        os.path.join(LOGOS_DIR, arquivo),
        folder="futsal/teams",
        public_id=public_id,
        overwrite=True,
    )
    return resultado["secure_url"]


def resetar(campeonato, edicao):
    """Apaga times, jogadores, jogos e estatísticas do campeonato (o campeonato fica)."""
    torneio = Tournament.query.filter_by(name=campeonato, edition=edicao).first()
    apagados = {"times": 0, "jogadores": 0, "jogos": 0}
    if not torneio:
        return apagados

    times = select(Team.id).where(Team.tournament_id == torneio.id)
    jogos = select(Match.id).where(Match.tournament_id == torneio.id)
    PlayerMatchStat.query.filter(
        or_(PlayerMatchStat.match_id.in_(jogos), PlayerMatchStat.team_id.in_(times))
    ).delete(synchronize_session=False)
    apagados["jogos"] = Match.query.filter_by(tournament_id=torneio.id).delete(
        synchronize_session=False
    )
    apagados["jogadores"] = Player.query.filter(Player.team_id.in_(times)).delete(
        synchronize_session=False
    )
    apagados["times"] = Team.query.filter_by(tournament_id=torneio.id).delete(
        synchronize_session=False
    )
    return apagados


def carregar(selecoes, jogadores, campeonato, edicao, simular=False):
    resumo = {"campeonato": "existente", "selecoes": 0, "jogadores": 0, "ignorados": 0}

    torneio = Tournament.query.filter_by(name=campeonato, edition=edicao).first()
    if not torneio:
        torneio = Tournament(name=campeonato, edition=edicao)
        db.session.add(torneio)
        db.session.flush()
        resumo["campeonato"] = "criado"

    times = {}
    for nome, dados in selecoes.items():
        time = Team.query.filter_by(name=nome, tournament_id=torneio.id).first()
        if not time:
            time = Team(name=nome, tournament_id=torneio.id)
            db.session.add(time)
            resumo["selecoes"] += 1
        time.acronym = dados["sigla"]
        # Arquivo local só na primeira carga (evita reenviar ao Cloudinary a cada
        # execução); link https da planilha sempre prevalece.
        if dados["logo"] and (not time.logo_filename or dados["logo"].startswith("https://")):
            time.logo_filename = (
                dados["logo"] if simular else resolver_logo(dados["logo"], nome)
            )
        times[nome] = time
    db.session.flush()

    # Comparação no Python: o lower() do SQLite ignora acentos ("Éverton" != "éverton").
    existentes = {}
    for j in jogadores:
        time = times[j["selecao"]]
        if time.id not in existentes:
            existentes[time.id] = {
                p.name.casefold() for p in Player.query.filter_by(team_id=time.id)
            }
        if j["nome"].casefold() in existentes[time.id]:
            resumo["ignorados"] += 1
            continue
        existentes[time.id].add(j["nome"].casefold())
        db.session.add(
            Player(name=j["nome"], team_id=time.id,
                   position=j["posicao"], shirt_number=j["camisa"])
        )
        resumo["jogadores"] += 1

    return torneio, resumo


def main():
    parser = argparse.ArgumentParser(description="Carga de seleções e jogadores via CSV.")
    parser.add_argument("planilha", help="Caminho do CSV (ex: dados/selecoes.csv)")
    parser.add_argument("--campeonato", required=True, help="Nome do campeonato")
    parser.add_argument("--edicao", default=None, help="Edição (ex: 2026)")
    parser.add_argument("--simular", action="store_true",
                        help="Valida e mostra o que seria feito, sem gravar nada")
    parser.add_argument("--resetar", action="store_true",
                        help="Apaga times, jogadores e jogos do campeonato antes de carregar")
    args = parser.parse_args()

    selecoes, jogadores, erros = validar(ler_planilha(args.planilha))
    if erros:
        print("Nada foi gravado. Corrija a planilha:")
        for e in erros:
            print(f"  - {e}")
        sys.exit(1)

    with app.app_context():
        banco = db.engine.url.render_as_string(hide_password=True)
        print(f"Banco: {banco}")

        if args.resetar:
            apagados = resetar(args.campeonato, args.edicao)
            print(f"Reset: {apagados['times']} times, {apagados['jogadores']} jogadores "
                  f"e {apagados['jogos']} jogos serão apagados deste campeonato.")
            if not args.simular and any(apagados.values()):
                # O pipe do PowerShell prefixa a entrada com BOM.
                resposta = input("Digite APAGAR para confirmar: ").replace("﻿", "")
                if resposta.strip() != "APAGAR":
                    db.session.rollback()
                    sys.exit("Cancelado, nada foi alterado.")

        torneio, resumo = carregar(
            selecoes, jogadores, args.campeonato, args.edicao, simular=args.simular
        )

        if args.simular:
            db.session.rollback()
            print("[SIMULAÇÃO] nada foi gravado.")
        else:
            db.session.commit()

        print(f"Campeonato: {torneio.display_name} ({resumo['campeonato']})")
        print(f"Seleções novas: {resumo['selecoes']} | Jogadores novos: {resumo['jogadores']} "
              f"| Jogadores já existentes (ignorados): {resumo['ignorados']}")


if __name__ == "__main__":
    main()
