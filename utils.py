import unidecode


def build_logo_filename(team_name: str) -> str:
    """Normaliza o nome do time para montar o nome do arquivo de logo."""
    logo_filename = (
        team_name.strip().replace(" ", "_").replace("-", "_").replace("&", "e").lower()
    )
    logo_filename = unidecode.unidecode(logo_filename)
    if logo_filename.endswith("_"):
        logo_filename = logo_filename[:-1]
    return logo_filename + ".jpg"
