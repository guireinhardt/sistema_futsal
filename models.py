from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, UniqueConstraint

db = SQLAlchemy()

class Team(db.Model):
    __tablename__ = 'team'  # É uma boa prática definir o nome da tabela
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    # Renomeando os backrefs para evitar conflitos
    matches_as_team_a = db.relationship('Match', foreign_keys='Match.team_a_id', backref='team_a_ref', lazy=True)
    matches_as_team_b = db.relationship('Match', foreign_keys='Match.team_b_id', backref='team_b_ref', lazy=True)
    players = db.relationship('Player', backref='team_ref')  # Renomeado para evitar conflito

class Match(db.Model):
    __tablename__ = 'match'  # Defina o nome da tabela
    id = db.Column(db.Integer, primary_key=True)
    team_a_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    team_b_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    score_a = db.Column(db.Integer, nullable=True)
    score_b = db.Column(db.Integer, nullable=True)

    # Renomeando os backrefs para evitar conflitos
    team_a = db.relationship('Team', foreign_keys=[team_a_id], backref='matches_as_team_a_ref')
    team_b = db.relationship('Team', foreign_keys=[team_b_id], backref='matches_as_team_b_ref')

class Player(db.Model):
    __tablename__ = 'player'  # Defina o nome da tabela
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    position = db.Column(db.String(30), nullable=False)  # Uma única posição
    goals = db.Column(db.Integer, default=0)

    team = db.relationship('Team', backref='players_list')  # Renomeado para evitar conflito

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