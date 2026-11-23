"""Copia todos os dados de um banco para outro banco vazio.

Uso típico: mudar o Neon de região (ex.: São Paulo -> Ohio, junto do Render).

    # PowerShell: as URLs valem só neste terminal; não coloque no .env
    $env:ORIGEM_DATABASE_URL  = "postgresql://...banco atual..."
    $env:DESTINO_DATABASE_URL = "postgresql://...banco novo, vazio..."
    python copiar_banco.py --simular   # só confere, não grava
    python copiar_banco.py             # cria as tabelas no destino e copia

O banco de origem só é lido, nunca alterado. O destino precisa estar vazio.
"""

import argparse
import os
import sys

from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.engine import make_url


def normalizar(url):
    for prefixo in ("postgres://", "postgresql://"):
        if url.startswith(prefixo):
            return "postgresql+psycopg2://" + url[len(prefixo):]
    return url


def ler_url(nome):
    url = os.environ.get(nome, "").strip()
    if not url:
        sys.exit(f"Defina {nome} no terminal antes de rodar (veja o topo deste arquivo).")
    return normalizar(url)


def versao_do_schema(engine):
    if "alembic_version" not in inspect(engine).get_table_names():
        return None
    with engine.connect() as c:
        return c.execute(text("select version_num from alembic_version")).scalar()


def main():
    parser = argparse.ArgumentParser(description="Copia os dados para um banco novo e vazio.")
    parser.add_argument("--simular", action="store_true",
                        help="Só confere origem e destino, sem gravar nada")
    args = parser.parse_args()

    origem_url = ler_url("ORIGEM_DATABASE_URL")
    destino_url = ler_url("DESTINO_DATABASE_URL")
    if make_url(origem_url).render_as_string(hide_password=True) == \
            make_url(destino_url).render_as_string(hide_password=True):
        sys.exit("Origem e destino são o mesmo banco.")

    # O app lê DATABASE_URL ao ser importado: aponta para o destino, para que
    # as migrations e as tabelas dos modelos sejam as do banco novo.
    os.environ["DATABASE_URL"] = destino_url
    os.environ.setdefault("SECRET_KEY", "copia-de-banco")
    from flask_migrate import upgrade
    from app import app
    from models import db

    origem = create_engine(origem_url)
    print(f"Origem:  {origem.url.render_as_string(hide_password=True)}")
    print(f"Destino: {make_url(destino_url).render_as_string(hide_password=True)}")

    tabelas = db.metadata.sorted_tables  # ordem que respeita as chaves estrangeiras
    with app.app_context():
        destino = db.engine

        versao_origem = versao_do_schema(origem)
        cabeca = _versao_cabeca(app)
        if versao_origem != cabeca:
            sys.exit(f"A origem está na migration {versao_origem}, mas o código está em "
                     f"{cabeca}. Faça o deploy (que atualiza a origem) antes de copiar.")

        existentes = set(inspect(destino).get_table_names())
        with destino.connect() as c:
            ocupadas = [t.name for t in tabelas if t.name in existentes
                        and c.execute(select(func.count()).select_from(t)).scalar()]
        if ocupadas:
            sys.exit(f"O destino já tem dados ({', '.join(ocupadas)}). "
                     "Use um banco vazio; nada foi alterado.")

        with origem.connect() as c:
            contagem = {t.name: c.execute(select(func.count()).select_from(t)).scalar()
                        for t in tabelas}
        for nome, n in contagem.items():
            print(f"  {nome:<18} {n:>5} linhas")

        if args.simular:
            print("[SIMULAÇÃO] Origem legível e destino vazio. Nada foi gravado.")
            return

        resposta = input("Digite COPIAR para criar as tabelas no destino e copiar: ")
        if resposta.replace("﻿", "").strip() != "COPIAR":
            sys.exit("Cancelado, nada foi alterado.")

        upgrade()  # cria as tabelas no destino, na mesma versão do código

        with origem.connect() as ler, destino.begin() as gravar:
            for tabela in tabelas:
                linhas = [dict(r._mapping) for r in ler.execute(select(tabela))]
                if linhas:
                    gravar.execute(tabela.insert(), linhas)
            if destino.dialect.name == "postgresql":
                # Os ids foram copiados prontos; o contador precisa continuar
                # depois do maior, senão o próximo cadastro dá id repetido.
                for tabela in tabelas:
                    if "id" in tabela.c:
                        gravar.execute(text(
                            f"select setval(pg_get_serial_sequence('{tabela.name}', 'id'), "
                            f"coalesce((select max(id) from {tabela.name}), 0) + 1, false)"
                        ))

        with destino.connect() as c:
            diferentes = [t.name for t in tabelas
                          if c.execute(select(func.count()).select_from(t)).scalar()
                          != contagem[t.name]]
        if diferentes:
            sys.exit(f"ATENÇÃO: contagem diferente em {', '.join(diferentes)}. "
                     "Não troque a URL no Render.")
        print("Cópia conferida: o destino tem as mesmas linhas da origem.")
        print("Agora troque DATABASE_URL no Render pela URL do destino.")


def _versao_cabeca(app):
    from alembic.script import ScriptDirectory

    config = app.extensions["migrate"].migrate.get_config()
    return ScriptDirectory.from_config(config).get_current_head()


if __name__ == "__main__":
    main()
