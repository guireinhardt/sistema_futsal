"""Testes de integração das rotas HTTP."""

import pytest
from models import db, Team, Player, Match, PlayerMatchStat


class TestRotasPublicas:
    def test_index(self, client):
        assert client.get("/").status_code == 200

    def test_standings(self, client, tournament):
        assert client.get("/standings").status_code == 200

    def test_matches(self, client, tournament):
        assert client.get("/matches").status_code == 200

    def test_players(self, client, tournament):
        assert client.get("/players").status_code == 200

    def test_top_scorers(self, client, tournament):
        assert client.get("/top_scorers").status_code == 200

    def test_404(self, client):
        assert client.get("/rota-inexistente").status_code == 404


class TestRotasTimes:
    def test_add_team_get(self, client, tournament):
        assert client.get("/add_team").status_code == 200

    def test_add_team_post(self, client, app, tournament):
        client.get(f"/tournament/select/{tournament.id}")
        client.post("/add_team", data={"name": "Novo Time"})
        with app.app_context():
            assert Team.query.filter_by(
                name="Novo Time", tournament_id=tournament.id
            ).first()

    def test_add_team_nome_vazio_retorna_form(self, client, tournament):
        client.get(f"/tournament/select/{tournament.id}")
        resp = client.post("/add_team", data={"name": ""})
        assert resp.status_code == 200


class TestRotasJogadores:
    def test_add_player_post(self, client, app, tournament, team_a):
        client.get(f"/tournament/select/{tournament.id}")
        client.post(
            "/add_player",
            data={
                "name": "Pedro Lima",
                "team_id": team_a.id,
                "position": "ala",
                "shirt_number": 7,
            },
        )
        with app.app_context():
            assert Player.query.filter_by(name="Pedro Lima").first()

    def test_edit_player_get(self, client, player_a):
        assert client.get(f"/edit_player/{player_a.id}").status_code == 200

    def test_edit_player_post(self, client, app, tournament, player_a, team_a):
        client.get(f"/tournament/select/{tournament.id}")
        client.post(
            f"/edit_player/{player_a.id}",
            data={
                "name": "João Atualizado",
                "team_id": team_a.id,
                "position": "fixo",
                "shirt_number": 99,
            },
        )
        with app.app_context():
            p = db.session.get(Player, player_a.id)
            assert p.name == "João Atualizado"
            assert p.shirt_number == 99

    def test_edit_player_404(self, client):
        assert client.get("/edit_player/99999").status_code == 404


class TestRotasPartidas:
    def test_add_match_get(self, client, tournament, team_a, team_b):
        client.get(f"/tournament/select/{tournament.id}")
        assert client.get("/add_match").status_code == 200

    def test_add_match_post(self, client, app, tournament, team_a, team_b):
        client.get(f"/tournament/select/{tournament.id}")
        client.post(
            "/add_match",
            data={
                "team_a_id": team_a.id,
                "team_b_id": team_b.id,
                "phase": "fase de grupos",
            },
        )
        with app.app_context():
            m = Match.query.filter_by(tournament_id=tournament.id).first()
            assert m is not None
            assert m.score_a is None

    def test_edit_match_post_salva_placar(
        self, client, app, pending_match, player_a, player_b
    ):
        client.post(
            f"/edit_match/{pending_match.id}",
            data={
                "score_a": 2,
                "score_b": 1,
                f"goals_a_{player_a.id}": 2,
                f"saves_a_{player_a.id}": 0,
                f"assists_a_{player_a.id}": 0,
                f"goals_b_{player_b.id}": 1,
                f"saves_b_{player_b.id}": 3,
                f"assists_b_{player_b.id}": 0,
            },
        )
        with app.app_context():
            m = db.session.get(Match, pending_match.id)
            assert m.score_a == 2
            assert m.score_b == 1

    def test_edit_match_stats_zerados_deletados(
        self, client, app, finished_match, player_a, team_a
    ):
        with app.app_context():
            db.session.add(
                PlayerMatchStat(
                    match_id=finished_match.id,
                    player_id=player_a.id,
                    team_id=team_a.id,
                    goals=1,
                    assists=0,
                    saves=0,
                )
            )
            db.session.commit()

        client.post(
            f"/edit_match/{finished_match.id}",
            data={
                "score_a": 0,
                "score_b": 0,
                f"goals_a_{player_a.id}": 0,
                f"saves_a_{player_a.id}": 0,
                f"assists_a_{player_a.id}": 0,
            },
        )
        with app.app_context():
            assert (
                PlayerMatchStat.query.filter_by(
                    match_id=finished_match.id, player_id=player_a.id
                ).first()
                is None
            )

    def test_edit_match_404(self, client):
        assert client.get("/edit_match/99999").status_code == 404

    def test_match_detail(self, client, finished_match):
        assert client.get(f"/match/{finished_match.id}").status_code == 200

    def test_match_detail_404(self, client):
        assert client.get("/match/99999").status_code == 404


class TestRotaClassificacao:
    def test_generate_semis_sem_grupos_completos(
        self, client, tournament, pending_match
    ):
        client.get(f"/tournament/select/{tournament.id}")
        client.post("/generate_semi_finals")
        with client.application.app_context():
            assert (
                Match.query.filter_by(
                    tournament_id=tournament.id, phase="semi-final"
                ).count()
                == 0
            )

    def test_generate_semis_com_grupos_completos(
        self, client, app, tournament, complete_group_stage
    ):
        client.get(f"/tournament/select/{tournament.id}")
        client.post("/generate_semi_finals")
        with app.app_context():
            assert (
                Match.query.filter_by(
                    tournament_id=tournament.id, phase="semi-final"
                ).count()
                == 2
            )

    def test_generate_semis_idempotente(
        self, client, app, tournament, complete_group_stage
    ):
        client.get(f"/tournament/select/{tournament.id}")
        client.post("/generate_semi_finals")
        client.post("/generate_semi_finals")
        with app.app_context():
            assert (
                Match.query.filter_by(
                    tournament_id=tournament.id, phase="semi-final"
                ).count()
                == 2
            )

    def test_generate_final(self, client, app, tournament, semi_finals_finished):
        client.get(f"/tournament/select/{tournament.id}")
        client.post("/generate_final")
        with app.app_context():
            assert (
                Match.query.filter_by(
                    tournament_id=tournament.id, phase="final"
                ).count()
                == 1
            )

    def test_generate_final_idempotente(
        self, client, app, tournament, semi_finals_finished
    ):
        client.get(f"/tournament/select/{tournament.id}")
        client.post("/generate_final")
        client.post("/generate_final")
        with app.app_context():
            assert (
                Match.query.filter_by(
                    tournament_id=tournament.id, phase="final"
                ).count()
                == 1
            )


class TestTopScorers:
    def test_sem_dados(self, client, tournament):
        assert client.get("/top_scorers").status_code == 200

    def test_com_stats(self, client, app, tournament, player_a, team_a, team_b):
        with app.app_context():
            m = Match(
                tournament_id=tournament.id,
                team_a_id=team_a.id,
                team_b_id=team_b.id,
                phase="fase de grupos",
                score_a=3,
                score_b=0,
            )
            db.session.add(m)
            db.session.commit()
            db.session.add(
                PlayerMatchStat(
                    match_id=m.id,
                    player_id=player_a.id,
                    team_id=team_a.id,
                    goals=3,
                    assists=1,
                    saves=0,
                )
            )
            db.session.commit()

        client.get(f"/tournament/select/{tournament.id}")
        resp = client.get("/top_scorers")
        assert "João Silva".encode() in resp.data
