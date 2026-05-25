from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, SubmitField, FileField
from wtforms.validators import DataRequired, NumberRange, Optional
from flask_wtf.file import FileAllowed


class TournamentForm(FlaskForm):
    name = StringField("Nome do campeonato", validators=[DataRequired()])
    edition = StringField("Edição (ex: 2025, 1ª edição)", validators=[Optional()])
    logo = FileField(
        "Logo do campeonato (JPG ou PNG, máx. 2MB)",
        validators=[FileAllowed(["jpg", "jpeg", "png"], "Apenas JPG ou PNG.")],
    )
    submit = SubmitField("Criar campeonato")


class TeamForm(FlaskForm):
    name = StringField("Nome do time", validators=[DataRequired()])
    logo = FileField(
        "Logo do time (JPG ou PNG, máx. 2MB)",
        validators=[FileAllowed(["jpg", "jpeg", "png"], "Apenas JPG ou PNG.")],
    )
    submit = SubmitField("Adicionar time")


class MatchForm(FlaskForm):
    team_a_id = SelectField("Time A", coerce=int, validators=[DataRequired()])
    team_b_id = SelectField("Time B", coerce=int, validators=[DataRequired()])
    phase = SelectField(
        "Fase",
        choices=[
            ("fase de grupos", "Fase de Grupos"),
            ("semi-final", "Semi-final"),
            ("final", "Final"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("Adicionar partida")


class PlayerForm(FlaskForm):
    name = StringField("Nome", validators=[DataRequired()])
    team_id = SelectField("Time", coerce=int, validators=[DataRequired()])
    position = SelectField(
        "Posição",
        choices=[
            ("goleiro", "Goleiro"),
            ("fixo", "Fixo"),
            ("ala", "Ala"),
            ("pivo", "Pivô"),
        ],
        validators=[DataRequired()],
    )
    shirt_number = IntegerField(
        "Número da camisa",
        validators=[DataRequired(), NumberRange(min=1, max=99)],
    )
    submit = SubmitField("Salvar jogador")
