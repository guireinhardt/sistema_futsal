from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, SubmitField,BooleanField
from wtforms.validators import DataRequired

class TeamForm(FlaskForm):
    name = StringField('Nome do Time', validators=[DataRequired()])
    submit = SubmitField('Adicionar Time')



class MatchForm(FlaskForm):
    team_a_id = SelectField('Time A', coerce=int, validators=[DataRequired()])
    team_b_id = SelectField('Time B', coerce=int, validators=[DataRequired()])
    
    # Novo campo de fase
    phase = SelectField('Fase da Partida', choices=[
        ('fase de grupos', 'Fase de Grupos'),
        ('semi-final', 'Semi-final'),
        ('final', 'Final')
    ], validators=[DataRequired()])

    submit = SubmitField('Adicionar Partida')

class PlayerForm(FlaskForm):
    name = StringField('Nome', validators=[DataRequired()])
    team_id = SelectField('Time', coerce=int, validators=[DataRequired()])
    position = SelectField('Posição', choices=[
        ('goleiro', 'Goleiro'),
        ('fixo', 'Fixo'),
        ('ala', 'Ala'),
        ('pivo', 'Pivô')
    ], validators=[DataRequired()])  # Adicionando validadores para o campo de posição
    goals = IntegerField('Gols', default=0)  # Adicionando o campo 'goals' corretamente
    submit = SubmitField('Adicionar Jogador')

