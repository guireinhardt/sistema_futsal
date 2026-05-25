from models import db, Match, Team


def calculate_standings(tournament_id):
    """
    Calcula a classificação da fase de grupos para um campeonato específico.
    Retorna lista ordenada por: pontos → saldo de gols → gols pró.
    """
    teams = Team.query.filter_by(tournament_id=tournament_id).all()
    standings = []

    for team in teams:
        matches = Match.query.filter(
            Match.tournament_id == tournament_id,
            Match.phase == "fase de grupos",
            db.or_(Match.team_a_id == team.id, Match.team_b_id == team.id),
            Match.score_a.isnot(None),
            Match.score_b.isnot(None),
        ).all()

        wins = draws = losses = goals_for = goals_against = 0

        for match in matches:
            if match.team_a_id == team.id:
                gf, ga = match.score_a, match.score_b
            else:
                gf, ga = match.score_b, match.score_a

            goals_for += gf
            goals_against += ga

            if gf > ga:
                wins += 1
            elif gf == ga:
                draws += 1
            else:
                losses += 1

        standings.append(
            {
                "team": team.name,
                "team_id": team.id,
                "played": wins + draws + losses,
                "wins": wins,
                "draws": draws,
                "losses": losses,
                "goals_for": goals_for,
                "goals_against": goals_against,
                "goal_diff": goals_for - goals_against,
                "points": wins * 3 + draws,
            }
        )

    standings.sort(
        key=lambda x: (x["points"], x["goal_diff"], x["goals_for"]),
        reverse=True,
    )
    return standings


def check_all_matches_completed(tournament_id):
    """True se todos os jogos de grupos do campeonato estão finalizados."""
    incomplete = Match.query.filter(
        Match.tournament_id == tournament_id,
        Match.phase == "fase de grupos",
        db.or_(Match.score_a.is_(None), Match.score_b.is_(None)),
    ).count()
    return incomplete == 0


def check_semi_finals_completed(tournament_id):
    """True se todas as semi-finais do campeonato estão finalizadas."""
    semis = Match.query.filter_by(tournament_id=tournament_id, phase="semi-final").all()
    if not semis:
        return False
    return all(m.score_a is not None and m.score_b is not None for m in semis)


def generate_semi_finals(standings_data):
    """1º vs 4º e 2º vs 3º. Retorna lista de dicts ou [] se < 4 times."""
    if len(standings_data) < 4:
        return []
    return [
        {
            "team_a_id": standings_data[0]["team_id"],
            "team_b_id": standings_data[3]["team_id"],
        },
        {
            "team_a_id": standings_data[1]["team_id"],
            "team_b_id": standings_data[2]["team_id"],
        },
    ]


def save_semi_finals(semi_finals, tournament_id):
    """Persiste as semi-finais. Idempotente — ignora se já existirem."""
    if (
        Match.query.filter_by(tournament_id=tournament_id, phase="semi-final").count()
        > 0
    ):
        return
    for sf in semi_finals:
        db.session.add(
            Match(
                tournament_id=tournament_id,
                team_a_id=sf["team_a_id"],
                team_b_id=sf["team_b_id"],
                phase="semi-final",
            )
        )
    db.session.commit()


def generate_final(semi_finals):
    """
    Determina os finalistas a partir das semi-finais já jogadas.
    Retorna dict {team_a_id, team_b_id} ou None se não for possível.
    """
    winners = []
    for match in semi_finals:
        if match.score_a is None or match.score_b is None:
            return None
        if match.winner is None:  # empate — futsal não deveria ter, mas tratamos
            return None
        winners.append(match.winner.id)

    if len(winners) != 2:
        return None

    return {"team_a_id": winners[0], "team_b_id": winners[1]}


def save_final(final_data, tournament_id):
    """Persiste a final. Idempotente — ignora se já existir."""
    if Match.query.filter_by(tournament_id=tournament_id, phase="final").count() > 0:
        return
    db.session.add(
        Match(
            tournament_id=tournament_id,
            team_a_id=final_data["team_a_id"],
            team_b_id=final_data["team_b_id"],
            phase="final",
        )
    )
    db.session.commit()
