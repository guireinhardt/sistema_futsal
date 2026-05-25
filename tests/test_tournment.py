"""
Testes específicos do Tournament:
- CRUD via rotas HTTP
- Isolamento entre campeonatos
- context_processor injeta active_tournament
"""

import pytest
from models import db, Tournament, Team, Match


class TestTournamentRoutes:
    def test_add_tournament_get(self, client):
        assert client.get("/tournament/new").status_code == 200

    def test_add_tournament_post_cria_e_seleciona(self, client, app):
        resp = client.post(
            "/tournament/new", data={"name": "Copa Verão", "edition": "2025"}
        )
        assert resp.status_code == 302
        with app.app_context():
            t = Tournament.query.filter_by(name="Copa Verão").first()
            assert t is not None
            assert t.edition == "2025"
            assert t.status == "em_andamento"

    def test_add_tournament_sem_nome_retorna_form(self, client):
        resp = client.post("/tournament/new", data={"name": "", "edition": ""})
        assert resp.status_code == 200

    def test_add_tournament_sem_edicao_ok(self, client, app):
        client.post("/tournament/new", data={"name": "Copa Sem Edição", "edition": ""})
        with app.app_context():
            t = Tournament.query.filter_by(name="Copa Sem Edição").first()
            assert t.edition is None

    def test_select_tournament(self, client, tournament):
        resp = client.get(f"/tournament/select/{tournament.id}")
        assert resp.status_code == 302
        with client.session_transaction() as sess:
            assert sess["tournament_id"] == tournament.id

    def test_select_tournament_inexistente_404(self, client):
        assert client.get("/tournament/select/99999").status_code == 404

    def test_finish_tournament(self, client, app, tournament):
        client.post(f"/tournament/finish/{tournament.id}")
        with app.app_context():
            t = db.session.get(Tournament, tournament.id)
            assert t.status == "finalizado"

    def test_index_lista_campeonatos(self, client, tournament):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Copa Teste".encode() in resp.data


class TestTournamentIsolation:
    def test_times_de_campeonatos_diferentes_nao_se_misturam(
        self, app, db, tournament, tournament_b
    ):
        """Times do campeonato A não aparecem nas queries do campeonato B."""
        with app.app_context():
            ta = Team(name="Time A", tournament_id=tournament.id)
            tb = Team(name="Time B", tournament_id=tournament_b.id)
            db.session.add_all([ta, tb])
            db.session.commit()

            times_a = Team.query.filter_by(tournament_id=tournament.id).all()
            times_b = Team.query.filter_by(tournament_id=tournament_b.id).all()

            assert all(t.tournament_id == tournament.id for t in times_a)
            assert all(t.tournament_id == tournament_b.id for t in times_b)
            assert len(times_a) == 1
            assert len(times_b) == 1

    def test_mesmo_nome_de_time_em_campeonatos_diferentes(
        self, app, db, tournament, tournament_b
    ):
        with app.app_context():
            db.session.add(Team(name="Leões FC", tournament_id=tournament.id))
            db.session.add(Team(name="Leões FC", tournament_id=tournament_b.id))
            db.session.commit()  # sem IntegrityError

    def test_partidas_isoladas_por_campeonato(self, app, db, tournament, tournament_b):
        with app.app_context():
            ta = Team(name="Time A", tournament_id=tournament.id)
            tb = Team(name="Time B", tournament_id=tournament_b.id)
            db.session.add_all([ta, tb])
            db.session.commit()

            m1 = Match(
                tournament_id=tournament.id,
                team_a_id=ta.id,
                team_b_id=ta.id,
                phase="fase de grupos",
                score_a=2,
                score_b=1,
            )
            m2 = Match(
                tournament_id=tournament_b.id,
                team_a_id=tb.id,
                team_b_id=tb.id,
                phase="fase de grupos",
                score_a=3,
                score_b=0,
            )
            db.session.add_all([m1, m2])
            db.session.commit()

            assert Match.query.filter_by(tournament_id=tournament.id).count() == 1
            assert Match.query.filter_by(tournament_id=tournament_b.id).count() == 1

    def test_rotas_sem_campeonato_redirecionam(self, client):
        """Sem nenhum campeonato no banco, rotas que dependem dele redirecionam."""
        # client usa db limpo (fixture db recria tudo do zero)
        for url in ["/add_team", "/players", "/matches", "/standings"]:
            resp = client.get(url)
            assert resp.status_code == 302, f"{url} deveria redirecionar sem campeonato"

    def test_context_processor_injeta_active_tournament(self, client, tournament):
        """active_tournament aparece no contexto de qualquer template."""
        resp = client.get("/")
        assert "Copa Teste".encode() in resp.data
