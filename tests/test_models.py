"""Testes dos modelos e suas propriedades."""

import pytest
from sqlalchemy.exc import IntegrityError
from models import db, Team, Player, Match, PlayerMatchStat


class TestMatchModel:
    def test_is_finished_true(self, finished_match):
        assert finished_match.is_finished is True

    def test_is_finished_false_score_none(self, pending_match):
        assert pending_match.is_finished is False

    def test_is_finished_false_score_a_none(self, db, tournament, team_a, team_b):
        m = Match(
            tournament_id=tournament.id,
            team_a_id=team_a.id,
            team_b_id=team_b.id,
            phase="fase de grupos",
            score_a=None,
            score_b=2,
        )
        db.session.add(m)
        db.session.commit()
        assert m.is_finished is False

    def test_winner_team_a(self, finished_match, team_a):
        assert finished_match.winner == team_a

    def test_winner_team_b(self, db, tournament, team_a, team_b):
        m = Match(
            tournament_id=tournament.id,
            team_a_id=team_a.id,
            team_b_id=team_b.id,
            phase="fase de grupos",
            score_a=0,
            score_b=2,
        )
        db.session.add(m)
        db.session.commit()
        assert m.winner == team_b

    def test_winner_draw_returns_none(self, db, tournament, team_a, team_b):
        m = Match(
            tournament_id=tournament.id,
            team_a_id=team_a.id,
            team_b_id=team_b.id,
            phase="fase de grupos",
            score_a=2,
            score_b=2,
        )
        db.session.add(m)
        db.session.commit()
        assert m.winner is None

    def test_winner_unfinished_returns_none(self, pending_match):
        assert pending_match.winner is None

    def test_repr(self, finished_match):
        assert "Leões FC" in repr(finished_match)
        assert "Tigres EC" in repr(finished_match)


class TestPlayerModel:
    def test_total_goals_zero_without_stats(self, player_a):
        assert player_a.total_goals == 0

    def test_total_goals_with_stats(self, db, tournament, player_a, team_a, team_b):
        m = Match(
            tournament_id=tournament.id,
            team_a_id=team_a.id,
            team_b_id=team_b.id,
            phase="fase de grupos",
            score_a=2,
            score_b=1,
        )
        db.session.add(m)
        db.session.commit()
        db.session.add(
            PlayerMatchStat(
                match_id=m.id,
                player_id=player_a.id,
                team_id=team_a.id,
                goals=2,
                assists=1,
                saves=0,
            )
        )
        db.session.commit()
        assert player_a.total_goals == 2

    def test_total_goals_sums_multiple_matches(
        self, db, tournament, player_a, team_a, team_b, team_c
    ):
        m1 = Match(
            tournament_id=tournament.id,
            team_a_id=team_a.id,
            team_b_id=team_b.id,
            phase="fase de grupos",
            score_a=3,
            score_b=0,
        )
        m2 = Match(
            tournament_id=tournament.id,
            team_a_id=team_a.id,
            team_b_id=team_c.id,
            phase="fase de grupos",
            score_a=2,
            score_b=1,
        )
        db.session.add_all([m1, m2])
        db.session.commit()
        db.session.add_all(
            [
                PlayerMatchStat(
                    match_id=m1.id,
                    player_id=player_a.id,
                    team_id=team_a.id,
                    goals=2,
                    assists=0,
                    saves=0,
                ),
                PlayerMatchStat(
                    match_id=m2.id,
                    player_id=player_a.id,
                    team_id=team_a.id,
                    goals=1,
                    assists=1,
                    saves=0,
                ),
            ]
        )
        db.session.commit()
        assert player_a.total_goals == 3
        assert player_a.total_assists == 1

    def test_repr(self, player_a):
        assert "João Silva" in repr(player_a)
        assert "#10" in repr(player_a)


class TestTeamModel:
    def test_unique_name_within_tournament(self, db, tournament, team_a):
        duplicate = Team(name="Leões FC", tournament_id=tournament.id)
        db.session.add(duplicate)
        with pytest.raises(IntegrityError):
            db.session.commit()

    def test_same_name_allowed_in_different_tournaments(
        self, db, tournament, tournament_b
    ):
        """Times com o mesmo nome podem existir em campeonatos diferentes."""
        t1 = Team(name="Leões FC", tournament_id=tournament.id)
        t2 = Team(name="Leões FC", tournament_id=tournament_b.id)
        db.session.add_all([t1, t2])
        db.session.commit()  # não deve lançar IntegrityError

    def test_team_players_relationship(self, team_a, player_a):
        assert player_a in team_a.players

    def test_repr(self, team_a):
        assert "Leões FC" in repr(team_a)


class TestPlayerMatchStatModel:
    def test_unique_constraint_match_player(self, db, finished_match, player_a, team_a):
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
        db.session.add(
            PlayerMatchStat(
                match_id=finished_match.id,
                player_id=player_a.id,
                team_id=team_a.id,
                goals=2,
                assists=0,
                saves=0,
            )
        )
        with pytest.raises(IntegrityError):
            db.session.commit()


class TestTournamentModel:
    def test_display_name_with_edition(self, tournament):
        assert tournament.display_name == "Copa Teste — 2025"

    def test_display_name_without_edition(self, db):
        t = Tournament(name="Copa Simples")
        db.session.add(t)
        db.session.commit()
        assert t.display_name == "Copa Simples"

    def test_default_status_is_em_andamento(self, tournament):
        assert tournament.status == "em_andamento"

    def test_repr(self, tournament):
        assert "Copa Teste" in repr(tournament)


# import necessário para o último teste
from models import Tournament
