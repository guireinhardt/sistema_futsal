from flask import Flask, flash,render_template, request, redirect, url_for
from models import db, Team, Player, Match
from forms import TeamForm, PlayerForm, MatchForm
from flask_wtf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'terca-f&era-cup'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///football.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
csrf = CSRFProtect(app)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_match', methods=['GET', 'POST'])
def add_match():
    form = MatchForm()  # Certifique-se de ter um formulário para adicionar partidas
    form.team_a_id.choices = [(team.id, team.name) for team in Team.query.all()]
    form.team_b_id.choices = [(team.id, team.name) for team in Team.query.all()]

    if form.validate_on_submit():
        team_a_id = form.team_a_id.data
        team_b_id = form.team_b_id.data
        score_a = form.score_a.data
        score_b = form.score_b.data

        # Criar nova partida
        match = Match(team_a_id=team_a_id, team_b_id=team_b_id, score_a=score_a, score_b=score_b)
        db.session.add(match)

        # Atualizar os gols dos jogadores
        players_a = Player.query.filter_by(team_id=team_a_id).all()
        players_b = Player.query.filter_by(team_id=team_b_id).all()

        if players_a:
            for player in players_a:
                player.goals += score_a // len(players_a)
        if players_b:
            for player in players_b:
                player.goals += score_b // len(players_b)

        db.session.commit()

        flash('Resultado da partida adicionado com sucesso!', 'success')
        return redirect(url_for('matches'))  # Redireciona para a tabela de partidas

    return render_template('add_match.html', form=form)


@app.route('/add_team', methods=['GET', 'POST'])
def add_team():
    form = TeamForm()
    if form.validate_on_submit():
        new_team = Team(name=form.name.data)
        db.session.add(new_team)
        db.session.commit()
        flash('Time adicionado com sucesso!', 'success')
        return redirect(url_for('index'))
    return render_template('add_team.html', form=form)

@app.route('/add_player', methods=['GET', 'POST'])
def add_player():
    form = PlayerForm()
    form.team_id.choices = [(team.id, team.name) for team in Team.query.all()]

    if form.validate_on_submit():
        player = Player(
            name=form.name.data,
            team_id=form.team_id.data,
            position=form.position.data,
            goals=form.goals.data  # Armazena a posição selecionada
        )
        db.session.add(player)
        db.session.commit()
        flash('Jogador adicionado com sucesso!', 'success')
        return redirect(url_for('players'))

    return render_template('add_player.html', form=form)



@app.route('/standings')
def standings():
    teams = Team.query.all()
    standings_data = []

    for team in teams:
        matches_as_team_a = Match.query.filter_by(team_a_id=team.id).all()
        matches_as_team_b = Match.query.filter_by(team_b_id=team.id).all()

        total_matches = len(matches_as_team_a) + len(matches_as_team_b)
        total_goals_scored = sum(match.score_a for match in matches_as_team_a) + sum(match.score_b for match in matches_as_team_b)
        total_goals_against = sum(match.score_b for match in matches_as_team_a) + sum(match.score_a for match in matches_as_team_b)
        goal_difference = total_goals_scored - total_goals_against

        wins = sum(1 for match in matches_as_team_a if match.score_a > match.score_b) + \
               sum(1 for match in matches_as_team_b if match.score_b > match.score_a)
        draws = sum(1 for match in matches_as_team_a if match.score_a == match.score_b) + \
                sum(1 for match in matches_as_team_b if match.score_b == match.score_a)
        losses = total_matches - (wins + draws)

        points = (wins * 3) + draws  # 3 pontos por vitória, 1 ponto por empate

        standings_data.append({
            'team': team.name,
            'matches': total_matches,
            'wins': wins,
            'draws': draws,
            'losses': losses,
            'goals_scored': total_goals_scored,
            'goals_against': total_goals_against,
            'goal_difference': goal_difference,
            'points': points,
        })

    standings_data.sort(key=lambda x: (x['points'], x['goal_difference'], x['goals_scored']), reverse=True)
    for index, team_data in enumerate(standings_data, start=1):
        team_data['position'] = index

    return render_template('standings.html', standings=standings_data)



@app.route('/top_scorers')
def top_scorers():
    players = Player.query.order_by(Player.goals.desc()).all()
    return render_template('top_scorers.html', players=players)


@app.route('/players')
def players():
    all_players = Player.query.all()  # Obtém todos os jogadores do banco de dados
    return render_template('players.html', players=all_players)
@app.route('/matches')
def matches():
    all_matches = Match.query.all()  # Obtém todos os jogos do banco de dados
    return render_template('matches.html', matches=all_matches)
@app.route('/edit_player/<int:player_id>', methods=['GET', 'POST'])
def edit_player(player_id):
    player = Player.query.get_or_404(player_id)
    form = PlayerForm()
    form.team_id.choices = [(team.id, team.name) for team in Team.query.all()]

    if form.validate_on_submit():
        player.name = form.name.data
        player.team_id = form.team_id.data
        player.position = form.position.data
        player.goals = form.goals.data  # Edita o número de gols
        db.session.commit()
        flash('Jogador atualizado com sucesso!', 'success')
        return redirect(url_for('players'))

    form.name.data = player.name
    form.team_id.data = player.team_id
    form.position.data = player.position
    form.goals.data = player.goals  # Preenche o campo de gols

    return render_template('edit_player.html', form=form, player=player)

@app.route('/edit_match/<int:match_id>', methods=['GET', 'POST'])
def edit_match(match_id):
    match = Match.query.get_or_404(match_id)
    
    if request.method == 'POST':
        match.score_a = request.form['score_a']
        match.score_b = request.form['score_b']
        db.session.commit()
        flash('Resultado da partida atualizado com sucesso!', 'success')
        return redirect(url_for('matches'))

    return render_template('edit_match.html', match=match)



if __name__ == '__main__':
    app.run(debug=True)
