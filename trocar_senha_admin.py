"""Gera uma nova senha forte e aleatória para o admin.

Uso:  python trocar_senha_admin.py

Mostra a senha uma única vez, pede confirmação de que foi salva, atualiza
ADMIN_PASSWORD_HASH no .env local e mostra o hash para colar no Render.
"""

import os
import re
import secrets
import string
import sys

from werkzeug.security import generate_password_hash

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
TAMANHO = 20
# Sem caracteres que se confundem ao ler/digitar (0/O, 1/l/I).
GRUPOS = [
    string.ascii_lowercase.replace("l", ""),
    string.ascii_uppercase.replace("O", "").replace("I", ""),
    "23456789",
    "-_!@#%+=",
]


def gerar_senha():
    todos = "".join(GRUPOS)
    while True:
        senha = "".join(secrets.choice(todos) for _ in range(TAMANHO))
        if all(any(c in grupo for c in senha) for grupo in GRUPOS):
            return senha


def atualizar_env(hash_senha):
    # Aspas simples: impedem que o "$" do hash seja interpretado como variável.
    linha = f"ADMIN_PASSWORD_HASH='{hash_senha}'"
    if not os.path.exists(ENV_PATH):
        print(f"Arquivo .env não encontrado em {ENV_PATH}; nada foi alterado.")
        return False
    with open(ENV_PATH, encoding="utf-8") as f:
        conteudo = f.read()
    padrao = re.compile(r"^ADMIN_PASSWORD_HASH=.*$", re.MULTILINE)
    if padrao.search(conteudo):
        conteudo = padrao.sub(lambda _: linha, conteudo)
    else:
        conteudo = conteudo.rstrip("\n") + "\n" + linha + "\n"
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write(conteudo)
    return True


def main():
    senha = gerar_senha()
    print("\nNova senha do admin (aparece só agora):\n")
    print(f"    {senha}\n")
    print("Salve no seu gerenciador de senhas antes de continuar.")
    if input("Já salvou? Digite s para aplicar: ").strip().lower() != "s":
        sys.exit("Cancelado, a senha atual continua valendo.")

    hash_senha = generate_password_hash(senha)
    if atualizar_env(hash_senha):
        print("\n.env local atualizado. Reinicie o servidor local para valer.")
    print("\nPara o Render, cole este valor em ADMIN_PASSWORD_HASH (Environment):\n")
    print(hash_senha)
    print("\nDepois de salvar no Render, ele reinicia o serviço sozinho.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        sys.exit("\nCancelado, a senha atual continua valendo.")
