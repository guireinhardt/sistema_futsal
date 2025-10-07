from flask import Flask, flash,render_template, request, redirect, url_for
from models import db, Team, Player, Match, PlayerMatchStat
from forms import TeamForm, PlayerForm, MatchForm
from flask_wtf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

app = Flask(__name__)
app.config['DEBUG'] = True
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
    form = MatchForm()

    # Preencher as escolhas dos times no formulário
    form.team_a_id.choices = [(team.id, team.name) for team in Team.query.all()]
    form.team_b_id.choices = [(team.id, team.name) for team in Team.query.all()]

    if form.validate_on_submit():  # Quando o formulário for enviado e validado
        team_a_id = form.team_a_id.data
        team_b_id = form.team_b_id.data

        # Criar nova partida com placar None (não finalizado)
        match = Match(team_a_id=team_a_id, team_b_id=team_b_id, score_a=None, score_b=None)
        db.session.add(match)
        db.session.commit()  # Commit para salvar a partida no banco

        flash('Partida adicionada com sucesso!', 'success')
        return redirect(url_for('matches'))  # Redireciona para a página de partidas

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

        total_matches = 0
        total_goals_scored = 0
        total_goals_against = 0
        goal_difference = 0

        wins = 0
        draws = 0
        losses = 0

        # Contabiliza apenas os jogos finalizados, ou empate 0x0
        for match in matches_as_team_a:
            if match.score_a is not None and match.score_b is not None:  # Jogo finalizado
                total_matches += 1
                total_goals_scored += match.score_a
                total_goals_against += match.score_b
                goal_difference += match.score_a - match.score_b

                if match.score_a > match.score_b:  # Vitória do Time A
                    wins += 1
                elif match.score_a == match.score_b:  # Empate (0x0)
                    draws += 1
                else:  # Derrota para o Time A
                    losses += 1

        for match in matches_as_team_b:
            if match.score_a is not None and match.score_b is not None:  # Jogo finalizado
                total_matches += 1
                total_goals_scored += match.score_b
                total_goals_against += match.score_a
                goal_difference += match.score_b - match.score_a

                if match.score_b > match.score_a:  # Vitória do Time B
                    wins += 1
                elif match.score_a == match.score_b:  # Empate (0x0)
                    draws += 1
                else:  # Derrota para o Time B
                    losses += 1

        points = (wins * 3) + (draws * 1)  # 3 pontos por vitória, 1 ponto por empate

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

    # Atribui a posição ao time
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

    players_a = Player.query.filter_by(team_id=match.team_a_id).order_by(Player.name).all()
    players_b = Player.query.filter_by(team_id=match.team_b_id).order_by(Player.name).all()

    if request.method == 'POST':
        # 1) salva o placar (sem vincular à soma dos artilheiros)
        match.score_a = int(request.form.get('score_a') or 0)
        match.score_b = int(request.form.get('score_b') or 0)

        # 2) lê os gols por jogador
        counts_a = {p.id: int(request.form.get(f'goals_a_{p.id}', 0) or 0) for p in players_a}
        counts_b = {p.id: int(request.form.get(f'goals_b_{p.id}', 0) or 0) for p in players_b}

        touched_ids = set()

        # upsert stats do Time A
        for pid, n in counts_a.items():
            stat = PlayerMatchStat.query.filter_by(match_id=match.id, player_id=pid).first()
            if n == 0:
                if stat:
                    db.session.delete(stat)  # remove linha se zerou
            else:
                if not stat:
                    stat = PlayerMatchStat(match_id=match.id, player_id=pid, team_id=match.team_a_id)
                    db.session.add(stat)
                stat.team_id = match.team_a_id  # garante time correto
                stat.goals = n
                touched_ids.add(pid)

        # upsert stats do Time B
        for pid, n in counts_b.items():
            stat = PlayerMatchStat.query.filter_by(match_id=match.id, player_id=pid).first()
            if n == 0:
                if stat:
                    db.session.delete(stat)
            else:
                if not stat:
                    stat = PlayerMatchStat(match_id=match.id, player_id=pid, team_id=match.team_b_id)
                    db.session.add(stat)
                stat.team_id = match.team_b_id
                stat.goals = n
                touched_ids.add(pid)

        db.session.commit()

        # 3) (opcional) atualizar o agregado Player.goals só dos jogadores tocados
        if touched_ids:
            rows = (
                db.session.query(PlayerMatchStat.player_id, func.coalesce(func.sum(PlayerMatchStat.goals), 0))
                .filter(PlayerMatchStat.player_id.in_(touched_ids))
                .group_by(PlayerMatchStat.player_id)
                .all()
            )
            totals = {pid: total for pid, total in rows}
            for player in Player.query.filter(Player.id.in_(touched_ids)).all():
                player.goals = totals.get(player.id, 0)
            db.session.commit()

        flash('Partida e artilheiros da partida salvos (independentes do placar).', 'success')
        return redirect(url_for('matches'))

    # GET: pré-preenche com o que já existe
    existing = {s.player_id: s.goals for s in PlayerMatchStat.query.filter_by(match_id=match.id).all()}

    return render_template(
        'edit_match.html',
        match=match,
        players_a=players_a,
        players_b=players_b,
        stats_by_player=existing  # dict {player_id: gols nesta partida}
    )



if __name__ == '__main__':
    app.run(debug=True)
