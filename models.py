from flask_sqlalchemy import SQLAlchemy

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
