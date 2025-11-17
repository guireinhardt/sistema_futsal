from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, UniqueConstraint

db = SQLAlchemy()

class Team(db.Model):
    __tablename__ = 'teams'  # Nome correto da tabela

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    # Relacionamentos com partidas
    matches_as_team_a = db.relationship('Match', foreign_keys='Match.team_a_id', back_populates='team_a', lazy=True)
    matches_as_team_b = db.relationship('Match', foreign_keys='Match.team_b_id', back_populates='team_b', lazy=True)

    # Relacionamento com jogadores
    players = db.relationship('Player', back_populates='team')  # Corrigido: back_populates agora é utilizado ao invés de 'backref'

class Match(db.Model):
    __tablename__ = 'matches'

    id = db.Column(db.Integer, primary_key=True)
    team_a_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)  # Altere 'teams' aqui
    team_b_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)  # E aqui também
    score_a = db.Column(db.Integer, nullable=True)
    score_b = db.Column(db.Integer, nullable=True)
    phase = db.Column(db.String(50), nullable=False)  # Campo para a fase (fase de grupos, semi-final, final)

    team_a = db.relationship('Team', foreign_keys=[team_a_id])
    team_b = db.relationship('Team', foreign_keys=[team_b_id])

    def __repr__(self):
        return f'<Match {self.team_a.name} vs {self.team_b.name}>'

class Player(db.Model):
    __tablename__ = 'player'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    
    # Correção para a tabela 'teams' (não 'team')
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)  # Alterado de 'team.id' para 'teams.id'
    
    position = db.Column(db.String(30), nullable=False)
    goals = db.Column(db.Integer, default=0)
    
    # Adicionando número da camiseta
    shirt_number = db.Column(db.Integer, nullable=False)  # Número da camiseta, altere para nullable=True se desejar que seja opcional

    # Relacionamento com o time, agora com back_populates
    team = db.relationship('Team', back_populates='players')  # 'team_ref' estava errado antes, 'backref' não é necessário se 'back_populates' for usado

    def __repr__(self):
        return f'<Player {self.name}, Shirt Number: {self.shirt_number}>'

class Goal(db.Model):
    __tablename__ = 'goal'
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)  # Corrigido para 'matches.id'
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)  # Corrigido para 'teams.id'
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=func.now())

    # Se você quiser adicionar mais campos:
    # minute = db.Column(db.Integer)
    # own_goal = db.Column(db.Boolean, default=False)

class PlayerMatchStat(db.Model):
    __tablename__ = 'player_match_stat'
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)  # Corrigido para 'matches.id'
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)  # Corrigido para 'teams.id'
    
    goals = db.Column(db.Integer, nullable=False, default=0)
    saves = db.Column(db.Integer, nullable=False, default=0)  # novo campo
    assists = db.Column(db.Integer, nullable=False, default=0)  # novo campo

    created_at = db.Column(db.DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('match_id', 'player_id', name='uq_stat_match_player'),
    )

    match_ref = db.relationship('Match', backref=db.backref('player_stats', cascade='all, delete-orphan', lazy=True))
    player_ref = db.relationship('Player', backref='match_stats')
    team_ref = db.relationship('Team')
