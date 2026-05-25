"""
Fixtures compartilhadas. Cada teste recebe banco SQLite em memória limpo.
"""

import os
import pytest

os.environ.setdefault("SECRET_KEY", "test-key")
os.environ.setdefault("DEBUG", "False")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app import app as flask_app
from models import db as _db, Tournament, Team, Player, Match, PlayerMatchStat

# ── App / DB ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def app():
    flask_app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        }
    )
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.drop_all()


@pytest.fixture(scope="function")
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app, db):
    with app.test_client() as c:
        yield c


# ── Tournament ────────────────────────────────────────────────────────────────


@pytest.fixture
def tournament(db):
    t = Tournament(name="Copa Teste", edition="2025")
    db.session.add(t)
    db.session.commit()
    return t


@pytest.fixture
def tournament_b(db):
    """Segundo campeonato — para testes de isolamento."""
    t = Tournament(name="Copa Isolamento", edition="2025")
    db.session.add(t)
    db.session.commit()
    return t


# ── Teams ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def team_a(db, tournament):
    t = Team(name="Leões FC", tournament_id=tournament.id)
    db.session.add(t)
    db.session.commit()
    return t


@pytest.fixture
def team_b(db, tournament):
    t = Team(name="Tigres EC", tournament_id=tournament.id)
    db.session.add(t)
    db.session.commit()
    return t


@pytest.fixture
def team_c(db, tournament):
    t = Team(name="Falcões SC", tournament_id=tournament.id)
    db.session.add(t)
    db.session.commit()
    return t


@pytest.fixture
def team_d(db, tournament):
    t = Team(name="Águias CF", tournament_id=tournament.id)
    db.session.add(t)
    db.session.commit()
    return t


@pytest.fixture
def four_teams(db, team_a, team_b, team_c, team_d):
    return [team_a, team_b, team_c, team_d]


# ── Players ───────────────────────────────────────────────────────────────────


@pytest.fixture
def player_a(db, team_a):
    p = Player(name="João Silva", team_id=team_a.id, position="ala", shirt_number=10)
    db.session.add(p)
    db.session.commit()
    return p


@pytest.fixture
def player_b(db, team_b):
    p = Player(
        name="Carlos Souza", team_id=team_b.id, position="goleiro", shirt_number=1
    )
    db.session.add(p)
    db.session.commit()
    return p


# ── Matches ───────────────────────────────────────────────────────────────────


@pytest.fixture
def finished_match(db, tournament, team_a, team_b):
    m = Match(
        tournament_id=tournament.id,
        team_a_id=team_a.id,
        team_b_id=team_b.id,
        phase="fase de grupos",
        score_a=3,
        score_b=1,
    )
    db.session.add(m)
    db.session.commit()
    return m


@pytest.fixture
def pending_match(db, tournament, team_a, team_b):
    m = Match(
        tournament_id=tournament.id,
        team_a_id=team_a.id,
        team_b_id=team_b.id,
        phase="fase de grupos",
    )
    db.session.add(m)
    db.session.commit()
    return m


@pytest.fixture
def complete_group_stage(db, tournament, four_teams):
    """
    Round-robin 4 times, todos finalizados.
    Classificação esperada:
      1º Leões  — 9 pts
      2º Tigres — 6 pts
      3º Falcões — 3 pts
      4º Águias  — 0 pts
    """
    ta, tb, tc, td = four_teams
    fixtures = [
        (ta.id, tb.id, 3, 1),
        (ta.id, tc.id, 2, 0),
        (ta.id, td.id, 4, 0),
        (tb.id, tc.id, 2, 1),
        (tb.id, td.id, 3, 0),
        (tc.id, td.id, 1, 0),
    ]
    ms = []
    for a_id, b_id, sa, sb in fixtures:
        m = Match(
            tournament_id=tournament.id,
            team_a_id=a_id,
            team_b_id=b_id,
            phase="fase de grupos",
            score_a=sa,
            score_b=sb,
        )
        db.session.add(m)
        ms.append(m)
    db.session.commit()
    return ms


@pytest.fixture
def semi_finals_finished(db, tournament, four_teams):
    """Leões vencem Águias; Falcões vencem Tigres."""
    ta, tb, tc, td = four_teams
    sf1 = Match(
        tournament_id=tournament.id,
        team_a_id=ta.id,
        team_b_id=td.id,
        phase="semi-final",
        score_a=3,
        score_b=1,
    )
    sf2 = Match(
        tournament_id=tournament.id,
        team_a_id=tb.id,
        team_b_id=tc.id,
        phase="semi-final",
        score_a=1,
        score_b=2,
    )
    db.session.add_all([sf1, sf2])
    db.session.commit()
    return [sf1, sf2]
