"""Testes de integração das rotas HTTP."""

import io
import re

import pytest
from PIL import Image
from app import limiter
from models import db, Tournament, Team, Player, Match, PlayerMatchStat


class TestSeguranca:
    def test_cabecalhos_de_seguranca(self, client):
        resp = client.get("/")
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert resp.headers["X-Content-Type-Options"] == "nosniff"

    @pytest.mark.parametrize(
        "destino", ["https://evil.com", "//evil.com", "/\\evil.com", "evil.com"]
    )
    def test_login_nao_redireciona_para_fora(self, client, destino):
        resp = client.post(
            "/login",
            query_string={"next": destino},
            data={"username": "admin", "password": "test-password"},
        )
        assert resp.status_code == 302
        assert resp.headers["Location"] == "/"

    def test_login_redireciona_para_pagina_interna(self, client):
        resp = client.post(
            "/login",
            query_string={"next": "/add_team"},
            data={"username": "admin", "password": "test-password"},
        )
        assert resp.headers["Location"] == "/add_team"

    def test_logout_por_post_desloga(self, auth_client):
        resp = auth_client.post("/logout")
        assert resp.status_code == 302
        assert "/login" in auth_client.get("/add_team").headers["Location"]

    def test_logout_por_get_nao_desloga(self, auth_client, tournament):
        assert auth_client.get("/logout").status_code == 405
        assert auth_client.get("/add_team").status_code == 200

    def test_logout_sem_token_csrf_nao_desloga(self, app, auth_client, tournament):
        app.config["WTF_CSRF_ENABLED"] = True
        try:
            assert auth_client.post("/logout").status_code == 400
        finally:
            app.config["WTF_CSRF_ENABLED"] = False
        assert auth_client.get("/add_team").status_code == 200

    def test_lista_de_jogos_nao_tem_sair(self, auth_client, tournament):
        assert b'action="/logout"' not in auth_client.get("/matches").data

    @pytest.mark.parametrize("pagina", ["/", "/standings", "/players"])
    def test_botao_sair_e_formulario_com_token(self, app, auth_client, tournament, pagina):
        app.config["WTF_CSRF_ENABLED"] = True
        try:
            html = auth_client.get(pagina).data.decode()
        finally:
            app.config["WTF_CSRF_ENABLED"] = False
        assert 'action="/logout" method="post"' in html
        assert 'name="csrf_token"' in html

    def test_upload_recusa_arquivo_que_nao_e_imagem(self, auth_client, app, tournament):
        auth_client.get(f"/tournament/select/{tournament.id}")
        falso = (io.BytesIO(b"<script>alert(1)</script>"), "logo.png")
        resp = auth_client.post(
            "/add_team",
            data={"name": "Time Falso", "acronym": "TFA", "logo": falso},
            content_type="multipart/form-data",
        )
        assert "não é uma imagem válida".encode() in resp.data
        with app.app_context():
            assert not Team.query.filter_by(name="Time Falso").first()

    def test_upload_aceita_png_valido(self, auth_client, app, tournament, tmp_path, monkeypatch):
        monkeypatch.setattr(app, "root_path", str(tmp_path))
        buf = io.BytesIO()
        Image.new("RGB", (10, 10), "red").save(buf, format="PNG")
        buf.seek(0)
        auth_client.get(f"/tournament/select/{tournament.id}")
        auth_client.post(
            "/add_team",
            data={"name": "Time Real", "acronym": "TRE", "logo": (buf, "logo.png")},
            content_type="multipart/form-data",
        )
        with app.app_context():
            assert Team.query.filter_by(name="Time Real").first().logo_filename == "time_real.jpg"


class TestEditarCampeonato:
    def test_requer_login(self, client, tournament):
        resp = client.get(f"/tournament/edit/{tournament.id}")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_404(self, auth_client):
        assert auth_client.get("/tournament/edit/99999").status_code == 404

    def test_get_mostra_dados_atuais(self, auth_client, tournament):
        assert b"Copa Teste" in auth_client.get(f"/tournament/edit/{tournament.id}").data

    def test_adiciona_logo_e_mantem_dados(self, auth_client, app, tournament, tmp_path, monkeypatch):
        monkeypatch.setattr(app, "root_path", str(tmp_path))
        buf = io.BytesIO()
        Image.new("RGB", (10, 10), "red").save(buf, format="PNG")
        buf.seek(0)
        auth_client.post(
            f"/tournament/edit/{tournament.id}",
            data={"name": "Copa Teste", "edition": "2025", "logo": (buf, "logo.png")},
            content_type="multipart/form-data",
        )
        with app.app_context():
            t = db.session.get(Tournament, tournament.id)
            assert t.logo_filename == f"tournament_{t.id}.jpg"
            assert t.name == "Copa Teste"
        assert (tmp_path / "static" / "logos" / t.logo_filename).exists()

    def test_sem_arquivo_preserva_logo(self, auth_client, app, tournament):
        with app.app_context():
            db.session.get(Tournament, tournament.id).logo_filename = "atual.jpg"
            db.session.commit()
        auth_client.post(
            f"/tournament/edit/{tournament.id}",
            data={"name": "Novo Nome", "edition": ""},
            content_type="multipart/form-data",
        )
        with app.app_context():
            t = db.session.get(Tournament, tournament.id)
            assert (t.name, t.edition, t.logo_filename) == ("Novo Nome", None, "atual.jpg")

    def test_recusa_arquivo_falso(self, auth_client, app, tournament):
        falso = (io.BytesIO(b"<script>alert(1)</script>"), "logo.png")
        resp = auth_client.post(
            f"/tournament/edit/{tournament.id}",
            data={"name": "Outro Nome", "logo": falso},
            content_type="multipart/form-data",
        )
        assert "não é uma imagem válida".encode() in resp.data
        with app.app_context():
            t = db.session.get(Tournament, tournament.id)
            assert (t.name, t.logo_filename) == ("Copa Teste", None)

    def test_link_aparece_para_admin(self, auth_client, tournament):
        assert b"Editar Campeonato" in auth_client.get("/").data


class TestSaude:
    def test_healthz(self, client):
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.get_json() == {"status": "ok"}


class TestRateLimitLogin:
    def test_login_bloqueia_apos_muitas_tentativas(self, app, client):
        limiter.enabled = True
        try:
            for _ in range(10):
                client.post("/login", data={"username": "x", "password": "y"})
            resp = client.post("/login", data={"username": "x", "password": "y"})
            assert resp.status_code == 429
        finally:
            limiter.enabled = False


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
    def test_add_team_get(self, auth_client, tournament):
        assert auth_client.get("/add_team").status_code == 200

    def test_add_team_requer_login(self, client, tournament):
        resp = client.get("/add_team")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_add_team_post(self, auth_client, app, tournament):
        auth_client.get(f"/tournament/select/{tournament.id}")
        auth_client.post("/add_team", data={"name": "Novo Time", "acronym": "NTM"})
        with app.app_context():
            assert Team.query.filter_by(
                name="Novo Time", tournament_id=tournament.id
            ).first()

    def test_add_team_nome_vazio_retorna_form(self, auth_client, tournament):
        auth_client.get(f"/tournament/select/{tournament.id}")
        resp = auth_client.post("/add_team", data={"name": "", "acronym": ""})
        assert resp.status_code == 200

    def test_edit_team_get(self, auth_client, team_a):
        assert auth_client.get(f"/edit_team/{team_a.id}").status_code == 200

    def test_edit_team_requer_login(self, client, team_a):
        resp = client.get(f"/edit_team/{team_a.id}")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_edit_team_post(self, auth_client, app, tournament, team_a):
        auth_client.get(f"/tournament/select/{tournament.id}")
        auth_client.post(
            f"/edit_team/{team_a.id}",
            data={"name": "Time Atualizado", "acronym": "TUA"},
        )
        with app.app_context():
            t = db.session.get(Team, team_a.id)
            assert t.name == "Time Atualizado"
            assert t.acronym == "TUA"

    def test_edit_team_corrige_acento_do_proprio_nome(self, auth_client, app, team_a):
        auth_client.post(
            f"/edit_team/{team_a.id}",
            data={"name": "LEÕES FC", "acronym": "LEO"},
            content_type="multipart/form-data",
        )
        with app.app_context():
            assert db.session.get(Team, team_a.id).name == "LEÕES FC"

    def test_edit_team_recusa_nome_de_outro_time(self, auth_client, app, team_a, team_b):
        resp = auth_client.post(
            f"/edit_team/{team_a.id}",
            data={"name": "tigres ec", "acronym": "TIG"},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        assert "Já existe um time".encode() in resp.data
        assert b'value="tigres ec"' in resp.data  # mantém o que foi digitado
        with app.app_context():
            assert db.session.get(Team, team_a.id).name == "Leões FC"

    def test_edit_team_recusa_sigla_longa(self, auth_client, app, team_a):
        resp = auth_client.post(
            f"/edit_team/{team_a.id}",
            data={"name": "Leões FC", "acronym": "LEOES"},
            content_type="multipart/form-data",
        )
        assert "Máximo de 4 letras".encode() in resp.data
        with app.app_context():
            assert db.session.get(Team, team_a.id).acronym != "LEOES"

    def test_add_team_tem_campo_sigla(self, auth_client, tournament):
        assert b'name="acronym"' in auth_client.get("/add_team").data

    def test_add_team_recusa_nome_repetido(self, auth_client, app, tournament, team_a):
        auth_client.get(f"/tournament/select/{tournament.id}")
        resp = auth_client.post("/add_team", data={"name": "LEÕES FC", "acronym": "LEO"})
        assert "Já existe um time".encode() in resp.data
        with app.app_context():
            assert Team.query.filter_by(tournament_id=tournament.id).count() == 1

    def test_edit_team_404(self, auth_client):
        assert auth_client.get("/edit_team/99999").status_code == 404


class TestRotasJogadores:
    def test_add_player_post(self, auth_client, app, tournament, team_a):
        auth_client.get(f"/tournament/select/{tournament.id}")
        auth_client.post(
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

    def test_edit_player_get(self, auth_client, player_a):
        assert auth_client.get(f"/edit_player/{player_a.id}").status_code == 200

    def test_edit_player_requer_login(self, client, player_a):
        resp = client.get(f"/edit_player/{player_a.id}")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_edit_player_post(self, auth_client, app, tournament, player_a, team_a):
        auth_client.get(f"/tournament/select/{tournament.id}")
        auth_client.post(
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

    def test_edit_player_tem_campo_camisa(self, auth_client, player_a):
        html = auth_client.get(f"/edit_player/{player_a.id}").data.decode()
        assert 'name="shirt_number"' in html
        assert 'value="10"' in html

    def test_edit_player_recusa_camisa_invalida(self, auth_client, app, tournament, player_a, team_a):
        auth_client.get(f"/tournament/select/{tournament.id}")
        resp = auth_client.post(
            f"/edit_player/{player_a.id}",
            data={"name": "João Silva", "team_id": team_a.id, "position": "ala", "shirt_number": 100},
        )
        assert resp.status_code == 200
        assert b'value="100"' in resp.data  # mantém o que foi digitado
        with app.app_context():
            assert db.session.get(Player, player_a.id).shirt_number == 10

    def test_edit_player_avisa_camisa_repetida_mas_salva(self, auth_client, app, tournament, player_a, team_a):
        with app.app_context():
            db.session.add(Player(name="Outro", team_id=team_a.id, position="fixo", shirt_number=7))
            db.session.commit()
        auth_client.get(f"/tournament/select/{tournament.id}")
        resp = auth_client.post(
            f"/edit_player/{player_a.id}",
            data={"name": "João Silva", "team_id": team_a.id, "position": "ala", "shirt_number": 7},
            follow_redirects=True,
        )
        assert "Outro também está com a camisa 7".encode() in resp.data
        with app.app_context():
            assert db.session.get(Player, player_a.id).shirt_number == 7

    def test_lista_mostra_numero_da_camisa(self, client, tournament, player_a):
        client.get(f"/tournament/select/{tournament.id}")
        assert "#10 · ala".encode() in client.get("/players").data

    def test_edit_player_404(self, auth_client):
        assert auth_client.get("/edit_player/99999").status_code == 404


class TestRotasPartidas:
    def test_add_match_get(self, auth_client, tournament, team_a, team_b):
        auth_client.get(f"/tournament/select/{tournament.id}")
        assert auth_client.get("/add_match").status_code == 200

    def test_add_match_requer_login(self, client, tournament, team_a, team_b):
        resp = client.get("/add_match")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_add_match_post(self, auth_client, app, tournament, team_a, team_b):
        auth_client.get(f"/tournament/select/{tournament.id}")
        auth_client.post(
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
        self, auth_client, app, pending_match, player_a, player_b
    ):
        auth_client.post(
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
        self, auth_client, app, finished_match, player_a, team_a
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

        auth_client.post(
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

    def test_edit_match_placar_em_branco_nao_finaliza(self, auth_client, app, pending_match):
        resp = auth_client.post(
            f"/edit_match/{pending_match.id}", data={"score_a": "", "score_b": "2"}
        )
        assert "Informe o placar".encode() in resp.data
        assert b'value="2"' in resp.data  # mantém o que foi digitado
        with app.app_context():
            assert not db.session.get(Match, pending_match.id).is_finished

    def test_edit_match_jogo_pendente_abre_sem_zero_no_placar(self, auth_client, pending_match):
        html = auth_client.get(f"/edit_match/{pending_match.id}").data.decode()
        assert re.search(r'name="score_a"[^>]*value=""', html)

    @pytest.mark.parametrize("valor", ["-1", "abc"])
    def test_edit_match_recusa_estatistica_invalida(self, auth_client, app, pending_match, player_a, valor):
        resp = auth_client.post(
            f"/edit_match/{pending_match.id}",
            data={"score_a": 1, "score_b": 0, f"goals_a_{player_a.id}": valor},
        )
        assert "números inteiros".encode() in resp.data
        with app.app_context():
            assert not db.session.get(Match, pending_match.id).is_finished

    def test_edit_match_avisa_gols_diferentes_do_placar(self, auth_client, pending_match, player_a, player_b):
        resp = auth_client.post(
            f"/edit_match/{pending_match.id}",
            data={"score_a": 3, "score_b": 0, f"goals_a_{player_a.id}": 2},
            follow_redirects=True,
        )
        assert "placar 3, mas 2 gol(s)".encode() in resp.data

    def test_edit_match_sem_aviso_quando_gols_batem(self, auth_client, pending_match, player_a, player_b):
        resp = auth_client.post(
            f"/edit_match/{pending_match.id}",
            data={"score_a": 2, "score_b": 0, f"goals_a_{player_a.id}": 2},
            follow_redirects=True,
        )
        assert "Atenção".encode() not in resp.data
        assert "Partida e estatísticas salvas".encode() in resp.data

    def test_edit_match_limpar_resultado(self, auth_client, app, finished_match, player_a):
        with app.app_context():
            db.session.add(PlayerMatchStat(
                match_id=finished_match.id, player_id=player_a.id,
                team_id=player_a.team_id, goals=3,
            ))
            db.session.commit()
        auth_client.post(f"/edit_match/{finished_match.id}", data={"acao": "limpar"})
        with app.app_context():
            assert not db.session.get(Match, finished_match.id).is_finished
            assert PlayerMatchStat.query.filter_by(match_id=finished_match.id).count() == 0

    def test_edit_match_nao_limpa_se_fase_seguinte_existe(self, auth_client, app, finished_match, tournament, team_a, team_b):
        with app.app_context():
            db.session.add(Match(
                tournament_id=tournament.id, team_a_id=team_a.id,
                team_b_id=team_b.id, phase="semi-final",
            ))
            db.session.commit()
        assert b'id="btn-limpar"' not in auth_client.get(f"/edit_match/{finished_match.id}").data
        resp = auth_client.post(f"/edit_match/{finished_match.id}", data={"acao": "limpar"})
        assert "não pode ser limpo".encode() in resp.data
        with app.app_context():
            assert db.session.get(Match, finished_match.id).is_finished

    def test_edit_match_ordena_goleiro_primeiro(self, auth_client, app, pending_match, team_a):
        with app.app_context():
            db.session.add_all([
                Player(name="Aaa Ala", team_id=team_a.id, position="ala", shirt_number=2),
                Player(name="Zzz Goleiro", team_id=team_a.id, position="goleiro", shirt_number=1),
            ])
            db.session.commit()
        html = auth_client.get(f"/edit_match/{pending_match.id}").data.decode()
        assert html.index("Zzz Goleiro") < html.index("Aaa Ala")
        assert "#1</span> Zzz Goleiro" in html

    def test_edit_match_mostra_fase(self, auth_client, pending_match):
        assert b"Fase de Grupos" in auth_client.get(f"/edit_match/{pending_match.id}").data

    def _semi(self, tournament, team_a, team_b):
        m = Match(tournament_id=tournament.id, team_a_id=team_a.id,
                  team_b_id=team_b.id, phase="semi-final")
        db.session.add(m)
        db.session.commit()
        return m.id

    def test_empate_eliminatorio_exige_penaltis(self, auth_client, app, tournament, team_a, team_b):
        mid = self._semi(tournament, team_a, team_b)
        resp = auth_client.post(f"/edit_match/{mid}", data={"score_a": 1, "score_b": 1})
        assert "informe os pênaltis".encode() in resp.data
        with app.app_context():
            assert not db.session.get(Match, mid).is_finished

    def test_penaltis_empatados_sao_recusados(self, auth_client, app, tournament, team_a, team_b):
        mid = self._semi(tournament, team_a, team_b)
        resp = auth_client.post(
            f"/edit_match/{mid}",
            data={"score_a": 1, "score_b": 1, "penalties_a": 3, "penalties_b": 3},
        )
        assert "informe os pênaltis".encode() in resp.data

    def test_penaltis_definem_vencedor(self, auth_client, app, tournament, team_a, team_b):
        mid = self._semi(tournament, team_a, team_b)
        auth_client.post(
            f"/edit_match/{mid}",
            data={"score_a": 1, "score_b": 1, "penalties_a": 3, "penalties_b": 4},
        )
        with app.app_context():
            assert db.session.get(Match, mid).winner.id == team_b.id
        assert "pên. 4".encode() in auth_client.get("/matches").data

    def test_penaltis_somem_quando_nao_ha_empate(self, auth_client, app, tournament, team_a, team_b):
        mid = self._semi(tournament, team_a, team_b)
        auth_client.post(
            f"/edit_match/{mid}",
            data={"score_a": 2, "score_b": 1, "penalties_a": 3, "penalties_b": 4},
        )
        with app.app_context():
            m = db.session.get(Match, mid)
            assert m.penalties_a is None and m.winner.id == team_a.id

    def test_fase_de_grupos_aceita_empate_sem_penaltis(self, auth_client, app, pending_match):
        auth_client.post(f"/edit_match/{pending_match.id}", data={"score_a": 1, "score_b": 1})
        with app.app_context():
            m = db.session.get(Match, pending_match.id)
            assert m.is_finished and m.winner is None

    def test_final_gerada_apos_semi_nos_penaltis(self, auth_client, app, tournament, four_teams):
        ta, tb, tc, td = four_teams
        with app.app_context():
            db.session.add_all([
                Match(tournament_id=tournament.id, team_a_id=ta.id, team_b_id=td.id,
                      phase="semi-final", score_a=2, score_b=2, penalties_a=5, penalties_b=4),
                Match(tournament_id=tournament.id, team_a_id=tb.id, team_b_id=tc.id,
                      phase="semi-final", score_a=0, score_b=1),
            ])
            db.session.commit()
        auth_client.get(f"/tournament/select/{tournament.id}")
        auth_client.post("/generate_final")
        with app.app_context():
            final = Match.query.filter_by(tournament_id=tournament.id, phase="final").one()
            assert {final.team_a_id, final.team_b_id} == {ta.id, tc.id}

    def test_edit_match_404(self, auth_client):
        assert auth_client.get("/edit_match/99999").status_code == 404

    def test_match_detail(self, client, finished_match):
        assert client.get(f"/match/{finished_match.id}").status_code == 200

    def test_match_detail_404(self, client):
        assert client.get("/match/99999").status_code == 404


class TestRotaClassificacao:
    def test_generate_semis_requer_login(self, client, tournament, pending_match):
        resp = client.post("/generate_semi_finals")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_generate_semis_sem_grupos_completos(
        self, auth_client, tournament, pending_match
    ):
        auth_client.get(f"/tournament/select/{tournament.id}")
        auth_client.post("/generate_semi_finals")
        with auth_client.application.app_context():
            assert (
                Match.query.filter_by(
                    tournament_id=tournament.id, phase="semi-final"
                ).count()
                == 0
            )

    def test_generate_semis_com_grupos_completos(
        self, auth_client, app, tournament, complete_group_stage
    ):
        auth_client.get(f"/tournament/select/{tournament.id}")
        auth_client.post("/generate_semi_finals")
        with app.app_context():
            assert (
                Match.query.filter_by(
                    tournament_id=tournament.id, phase="semi-final"
                ).count()
                == 2
            )

    def test_generate_semis_idempotente(
        self, auth_client, app, tournament, complete_group_stage
    ):
        auth_client.get(f"/tournament/select/{tournament.id}")
        auth_client.post("/generate_semi_finals")
        auth_client.post("/generate_semi_finals")
        with app.app_context():
            assert (
                Match.query.filter_by(
                    tournament_id=tournament.id, phase="semi-final"
                ).count()
                == 2
            )

    def test_generate_final(self, auth_client, app, tournament, semi_finals_finished):
        auth_client.get(f"/tournament/select/{tournament.id}")
        auth_client.post("/generate_final")
        with app.app_context():
            assert (
                Match.query.filter_by(
                    tournament_id=tournament.id, phase="final"
                ).count()
                == 1
            )

    def test_generate_final_idempotente(
        self, auth_client, app, tournament, semi_finals_finished
    ):
        auth_client.get(f"/tournament/select/{tournament.id}")
        auth_client.post("/generate_final")
        auth_client.post("/generate_final")
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
