"""Testes do standingsService — classificação, semi-finais, final."""

import pytest
from models import db, Match
from services.standingsService import (
    calculate_standings,
    check_all_matches_completed,
    check_semi_finals_completed,
    generate_semi_finals,
    save_semi_finals,
    generate_final,
    save_final,
)


class TestCalculateStandings:
    def test_ordem_correta(self, app, complete_group_stage, four_teams, tournament):
        with app.app_context():
            s = calculate_standings(tournament.id)
            assert [r["team"] for r in s] == [
                "Leões FC",
                "Tigres EC",
                "Falcões SC",
                "Águias CF",
            ]

    def test_pontuacao(self, app, complete_group_stage, tournament):
        with app.app_context():
            s = calculate_standings(tournament.id)
            leoes = next(r for r in s if r["team"] == "Leões FC")
            assert leoes["points"] == 9
            assert leoes["wins"] == 3

    def test_saldo_de_gols(self, app, complete_group_stage, tournament):
        with app.app_context():
            s = calculate_standings(tournament.id)
            leoes = next(r for r in s if r["team"] == "Leões FC")
            assert leoes["goals_for"] == 9
            assert leoes["goals_against"] == 1
            assert leoes["goal_diff"] == 8

    def test_sem_partidas_todos_zerados(self, app, four_teams, tournament):
        with app.app_context():
            s = calculate_standings(tournament.id)
            assert len(s) == 4
            assert all(r["points"] == 0 for r in s)

    def test_ignora_outros_campeonatos(
        self, app, complete_group_stage, tournament, tournament_b, db
    ):
        """Partidas de outro campeonato não entram na classificação."""
        with app.app_context():
            # cria time e partida no campeonato B
            from models import Team

            t_extra = Team(name="Invasores", tournament_id=tournament_b.id)
            db.session.add(t_extra)
            db.session.commit()
            m_extra = Match(
                tournament_id=tournament_b.id,
                team_a_id=t_extra.id,
                team_b_id=t_extra.id,
                phase="fase de grupos",
                score_a=5,
                score_b=0,
            )
            db.session.add(m_extra)
            db.session.commit()

            s = calculate_standings(tournament.id)
            names = [r["team"] for r in s]
            assert "Invasores" not in names

    def test_empate_gera_um_ponto_cada(self, app, tournament, four_teams):
        with app.app_context():
            ta, tb = four_teams[0], four_teams[1]
            db.session.add(
                Match(
                    tournament_id=tournament.id,
                    team_a_id=ta.id,
                    team_b_id=tb.id,
                    phase="fase de grupos",
                    score_a=1,
                    score_b=1,
                )
            )
            db.session.commit()
            s = calculate_standings(tournament.id)
            for r in s:
                if r["team"] in ("Leões FC", "Tigres EC"):
                    assert r["points"] == 1


class TestCheckAllMatchesCompleted:
    def test_true_quando_todos_finalizados(self, app, complete_group_stage, tournament):
        with app.app_context():
            assert check_all_matches_completed(tournament.id) is True

    def test_false_quando_ha_pendentes(self, app, pending_match, tournament):
        with app.app_context():
            assert check_all_matches_completed(tournament.id) is False

    def test_true_sem_nenhuma_partida(self, app, tournament):
        with app.app_context():
            assert check_all_matches_completed(tournament.id) is True

    def test_nao_afeta_outro_campeonato(
        self, app, pending_match, tournament, tournament_b, db
    ):
        """Partida pendente no campeonato A não interfere no B."""
        with app.app_context():
            assert check_all_matches_completed(tournament_b.id) is True


class TestCheckSemiFinalsCompleted:
    def test_false_sem_semis(self, app, tournament):
        with app.app_context():
            assert check_semi_finals_completed(tournament.id) is False

    def test_true_quando_finalizadas(self, app, semi_finals_finished, tournament):
        with app.app_context():
            assert check_semi_finals_completed(tournament.id) is True

    def test_false_quando_uma_pendente(self, app, tournament, four_teams):
        with app.app_context():
            ta, tb, tc, td = four_teams
            db.session.add_all(
                [
                    Match(
                        tournament_id=tournament.id,
                        team_a_id=ta.id,
                        team_b_id=td.id,
                        phase="semi-final",
                        score_a=2,
                        score_b=0,
                    ),
                    Match(
                        tournament_id=tournament.id,
                        team_a_id=tb.id,
                        team_b_id=tc.id,
                        phase="semi-final",
                    ),
                ]
            )
            db.session.commit()
            assert check_semi_finals_completed(tournament.id) is False


class TestGenerateSemiFinals:
    def test_gera_1vs4_e_2vs3(self, app, complete_group_stage, tournament):
        with app.app_context():
            s = calculate_standings(tournament.id)
            semis = generate_semi_finals(s)
            assert len(semis) == 2
            assert semis[0] == {
                "team_a_id": s[0]["team_id"],
                "team_b_id": s[3]["team_id"],
            }
            assert semis[1] == {
                "team_a_id": s[1]["team_id"],
                "team_b_id": s[2]["team_id"],
            }

    def test_vazio_com_menos_de_4(self, app, tournament):
        with app.app_context():
            assert generate_semi_finals([]) == []


class TestSaveSemiFinals:
    def test_salva_duas_semis(self, app, complete_group_stage, tournament):
        with app.app_context():
            s = calculate_standings(tournament.id)
            semis = generate_semi_finals(s)
            save_semi_finals(semis, tournament.id)
            assert (
                Match.query.filter_by(
                    tournament_id=tournament.id, phase="semi-final"
                ).count()
                == 2
            )

    def test_idempotente(self, app, complete_group_stage, tournament):
        with app.app_context():
            s = calculate_standings(tournament.id)
            semis = generate_semi_finals(s)
            save_semi_finals(semis, tournament.id)
            save_semi_finals(semis, tournament.id)  # segunda chamada ignorada
            assert (
                Match.query.filter_by(
                    tournament_id=tournament.id, phase="semi-final"
                ).count()
                == 2
            )

    def test_sem_placar_inicial(self, app, complete_group_stage, tournament):
        with app.app_context():
            save_semi_finals(
                generate_semi_finals(calculate_standings(tournament.id)), tournament.id
            )
            for m in Match.query.filter_by(
                tournament_id=tournament.id, phase="semi-final"
            ).all():
                assert m.score_a is None

    def test_nao_cria_semis_no_outro_campeonato(
        self, app, complete_group_stage, tournament, tournament_b
    ):
        with app.app_context():
            save_semi_finals(
                generate_semi_finals(calculate_standings(tournament.id)), tournament.id
            )
            assert (
                Match.query.filter_by(
                    tournament_id=tournament_b.id, phase="semi-final"
                ).count()
                == 0
            )


class TestGenerateFinal:
    def test_finalistas_corretos(
        self, app, semi_finals_finished, tournament, four_teams
    ):
        with app.app_context():
            ta, tb, tc, td = four_teams
            semis = Match.query.filter_by(
                tournament_id=tournament.id, phase="semi-final"
            ).all()
            fd = generate_final(semis)
            # sf1: Leões(ta) 3×1 Águias(td) → Leões; sf2: Tigres(tb) 1×2 Falcões(tc) → Falcões
            assert {fd["team_a_id"], fd["team_b_id"]} == {ta.id, tc.id}

    def test_none_com_semi_pendente(self, app, tournament, four_teams):
        with app.app_context():
            ta, tb, tc, td = four_teams
            db.session.add_all(
                [
                    Match(
                        tournament_id=tournament.id,
                        team_a_id=ta.id,
                        team_b_id=td.id,
                        phase="semi-final",
                        score_a=2,
                        score_b=0,
                    ),
                    Match(
                        tournament_id=tournament.id,
                        team_a_id=tb.id,
                        team_b_id=tc.id,
                        phase="semi-final",
                    ),
                ]
            )
            db.session.commit()
            semis = Match.query.filter_by(
                tournament_id=tournament.id, phase="semi-final"
            ).all()
            assert generate_final(semis) is None

    def test_none_com_empate(self, app, tournament, four_teams):
        with app.app_context():
            ta, tb, tc, td = four_teams
            db.session.add_all(
                [
                    Match(
                        tournament_id=tournament.id,
                        team_a_id=ta.id,
                        team_b_id=td.id,
                        phase="semi-final",
                        score_a=1,
                        score_b=1,
                    ),
                    Match(
                        tournament_id=tournament.id,
                        team_a_id=tb.id,
                        team_b_id=tc.id,
                        phase="semi-final",
                        score_a=2,
                        score_b=0,
                    ),
                ]
            )
            db.session.commit()
            semis = Match.query.filter_by(
                tournament_id=tournament.id, phase="semi-final"
            ).all()
            assert generate_final(semis) is None


class TestSaveFinal:
    def test_salva_a_final(self, app, semi_finals_finished, tournament):
        with app.app_context():
            semis = Match.query.filter_by(
                tournament_id=tournament.id, phase="semi-final"
            ).all()
            save_final(generate_final(semis), tournament.id)
            f = Match.query.filter_by(
                tournament_id=tournament.id, phase="final"
            ).first()
            assert f is not None
            assert f.score_a is None

    def test_idempotente(self, app, semi_finals_finished, tournament):
        with app.app_context():
            semis = Match.query.filter_by(
                tournament_id=tournament.id, phase="semi-final"
            ).all()
            fd = generate_final(semis)
            save_final(fd, tournament.id)
            save_final(fd, tournament.id)
            assert (
                Match.query.filter_by(
                    tournament_id=tournament.id, phase="final"
                ).count()
                == 1
            )

    def test_nao_cria_final_no_outro_campeonato(
        self, app, semi_finals_finished, tournament, tournament_b
    ):
        with app.app_context():
            semis = Match.query.filter_by(
                tournament_id=tournament.id, phase="semi-final"
            ).all()
            save_final(generate_final(semis), tournament.id)
            assert (
                Match.query.filter_by(
                    tournament_id=tournament_b.id, phase="final"
                ).count()
                == 0
            )
