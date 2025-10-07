from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, UniqueConstraint

db = SQLAlchemy()

class Team(db.Model):
    __tablename__ = 'team'  # Nome da tabela
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    # Relacionamentos com partidas, usando back_populates
    matches_as_team_a = db.relationship('Match', foreign_keys='Match.team_a_id', back_populates='team_a', lazy=True)
    matches_as_team_b = db.relationship('Match', foreign_keys='Match.team_b_id', back_populates='team_b', lazy=True)

    players = db.relationship('Player', backref='team_ref')  # Relacionamento com os jogadores

class Match(db.Model):
    __tablename__ = 'match'  # Nome da tabela
    id = db.Column(db.Integer, primary_key=True)
    team_a_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    team_b_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    
    # Alterando para permitir valores None (não atribuindo valor padrão)
    score_a = db.Column(db.Integer, nullable=True)  # Permite valores None
    score_b = db.Column(db.Integer, nullable=True)  # Permite valores None

    # Relacionamentos com as equipes, usando back_populates
    team_a = db.relationship('Team', foreign_keys=[team_a_id], back_populates='matches_as_team_a')
    team_b = db.relationship('Team', foreign_keys=[team_b_id], back_populates='matches_as_team_b')


class Player(db.Model):
    __tablename__ = 'player'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    position = db.Column(db.String(30), nullable=False)
    goals = db.Column(db.Integer, default=0)

    # Relacionamento com o time, agora com back_populates
    team = db.relationship('Team', back_populates='players', uselist=False)  # Relacionamento com o time (1:1)


class Goal(db.Model):
    __tablename__ = 'goal'
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=func.now())
    # Se quiser, acrescente:
    # minute = db.Column(db.Integer)
    # own_goal = db.Column(db.Boolean, default=False)

class PlayerMatchStat(db.Model):
    __tablename__ = 'player_match_stat'
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    goals = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('match_id', 'player_id', name='uq_stat_match_player'),
    )

    # relacionamentos úteis (opcionais)
    match_ref = db.relationship('Match', backref=db.backref('player_stats', cascade='all, delete-orphan', lazy=True))
    player_ref = db.relationship('Player', backref='match_stats')
    team_ref = db.relationship('Team')