from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, UniqueConstraint

db = SQLAlchemy()


# ──────────────────────────────────────────────────────────────────────────────
# Tournament
# ──────────────────────────────────────────────────────────────────────────────


class Tournament(db.Model):
    __tablename__ = "tournaments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    edition = db.Column(db.String(30), nullable=True)  # ex: "2025", "1ª edição"
    status = db.Column(db.String(20), nullable=False, default="em_andamento")
    # status: 'em_andamento' | 'finalizado'
    created_at = db.Column(db.DateTime, server_default=func.now())
    logo_filename = db.Column(
        db.String(120), nullable=True
    )  # logo do campeonato em static/logos/

    teams = db.relationship("Team", back_populates="tournament", lazy=True)
    matches = db.relationship("Match", back_populates="tournament", lazy=True)

    @property
    def display_name(self):
        if self.edition:
            return f"{self.name} — {self.edition}"
        return self.name

    def __repr__(self):
        return f"<Tournament {self.display_name}>"


# ──────────────────────────────────────────────────────────────────────────────
# Team
# ──────────────────────────────────────────────────────────────────────────────


class Team(db.Model):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    logo_filename = db.Column(
        db.String(120), nullable=True
    )  # nome do arquivo em static/logos/
    tournament_id = db.Column(
        db.Integer, db.ForeignKey("tournaments.id"), nullable=False
    )

    # Nome único DENTRO do campeonato, não globalmente
    __table_args__ = (
        UniqueConstraint("name", "tournament_id", name="uq_team_name_tournament"),
    )

    tournament = db.relationship("Tournament", back_populates="teams")
    matches_as_team_a = db.relationship(
        "Match", foreign_keys="Match.team_a_id", back_populates="team_a", lazy=True
    )
    matches_as_team_b = db.relationship(
        "Match", foreign_keys="Match.team_b_id", back_populates="team_b", lazy=True
    )
    players = db.relationship("Player", back_populates="team")

    def __repr__(self):
        return f"<Team {self.name}>"


# ──────────────────────────────────────────────────────────────────────────────
# Match
# ──────────────────────────────────────────────────────────────────────────────


class Match(db.Model):
    __tablename__ = "matches"

    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(
        db.Integer, db.ForeignKey("tournaments.id"), nullable=False
    )
    team_a_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    team_b_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    score_a = db.Column(db.Integer, nullable=True)
    score_b = db.Column(db.Integer, nullable=True)
    phase = db.Column(db.String(50), nullable=False)
    # phase: 'fase de grupos' | 'semi-final' | 'final'

    tournament = db.relationship("Tournament", back_populates="matches")
    team_a = db.relationship(
        "Team", foreign_keys=[team_a_id], back_populates="matches_as_team_a"
    )
    team_b = db.relationship(
        "Team", foreign_keys=[team_b_id], back_populates="matches_as_team_b"
    )

    @property
    def is_finished(self):
        return self.score_a is not None and self.score_b is not None

    @property
    def winner(self):
        if not self.is_finished:
            return None
        if self.score_a > self.score_b:
            return self.team_a
        if self.score_b > self.score_a:
            return self.team_b
        return None  # empate

    def __repr__(self):
        return f"<Match {self.team_a.name} vs {self.team_b.name}>"


# ──────────────────────────────────────────────────────────────────────────────
# Player  (não tem tournament_id — pertence ao time, que pertence ao campeonato)
# ──────────────────────────────────────────────────────────────────────────────


class Player(db.Model):
    __tablename__ = "player"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    position = db.Column(db.String(30), nullable=False)
    shirt_number = db.Column(db.Integer, nullable=False)

    team = db.relationship("Team", back_populates="players")

    @property
    def total_goals(self):
        return sum(s.goals for s in self.match_stats)

    @property
    def total_assists(self):
        return sum(s.assists for s in self.match_stats)

    @property
    def total_saves(self):
        return sum(s.saves for s in self.match_stats)

    def __repr__(self):
        return f"<Player {self.name} #{self.shirt_number}>"


# ──────────────────────────────────────────────────────────────────────────────
# PlayerMatchStat
# ──────────────────────────────────────────────────────────────────────────────


class PlayerMatchStat(db.Model):
    __tablename__ = "player_match_stat"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("player.id"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    goals = db.Column(db.Integer, nullable=False, default=0)
    saves = db.Column(db.Integer, nullable=False, default=0)
    assists = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("match_id", "player_id", name="uq_stat_match_player"),
    )

    match_ref = db.relationship(
        "Match",
        backref=db.backref("player_stats", cascade="all, delete-orphan", lazy=True),
    )
    player_ref = db.relationship("Player", backref="match_stats")
    team_ref = db.relationship("Team")
