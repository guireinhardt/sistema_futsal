from flask import Flask, flash,render_template, request, redirect, url_for
from models import db, Team, Player, Match, PlayerMatchStat
from forms import TeamForm, PlayerForm, MatchForm
from flask_wtf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from services.standingsService import calculate_standings,check_all_matches_completed,generate_semi_finals,save_semi_finals
import unidecode
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
        phase = form.phase.data  # Captura a fase selecionada no formulário

        # Criar nova partida com placar None (não finalizado)
        match = Match(team_a_id=team_a_id, team_b_id=team_b_id, phase=phase, score_a=None, score_b=None)
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
            goals=form.goals.data,  # Armazena a quantidade de gols
            shirt_number=form.shirt_number.data  # Agora estamos passando o número da camiseta
        )
        db.session.add(player)
        db.session.commit()
        flash('Jogador adicionado com sucesso!', 'success')
        return redirect(url_for('players'))

    return render_template('add_player.html', form=form)


@app.route('/standings')
def standings():
    # Verifica se todos os jogos da fase de grupos foram finalizados
    all_matches_completed = check_all_matches_completed()

    # Calcula a classificação geral
    standings_data = calculate_standings()

    # Adiciona o logo em cada time
    for data in standings_data:
        team_name = data["team"]  # ou data.team se for objeto
        data["logo_filename"] = build_logo_filename(team_name)  # Aplica a função para gerar o nome correto do logo

    # Buscar partidas da semi-final e final do banco
    semi_finals = Match.query.filter_by(phase='semi-final').all() if all_matches_completed else []
    final_matches = Match.query.filter_by(phase='final').all() if all_matches_completed else []

    return render_template(
        'standings.html',
        standings=standings_data,
        semi_finals=semi_finals,
        final_matches=final_matches,
        all_matches_completed=all_matches_completed
    )



@app.route('/top_scorers')
def top_scorers():
    players = Player.query.order_by(Player.goals.desc()).limit(10).all()
    return render_template('top_scorers.html', players=players)


@app.route('/players')
def players():
    teams = Team.query.all()  # Consulta todos os times
    for team in teams:
        # Verifica se o nome contém caracteres especiais que precisam ser tratados
        logo_filename = team.name.strip().replace(" ", "_").replace("-", "_").replace("&", "e").lower()
        
        # Se o nome não precisar de modificações, mantém ele sem underscore extra
        if logo_filename.endswith('_'):
            logo_filename = logo_filename[:-1]  # Remove o underscore final

        team.logo_filename = logo_filename + '.jpg'  # Adiciona a extensão .jpg ao nome do arquivo

    return render_template('players.html', teams=teams)

@app.route('/matches')
def matches():
    # Verifica se todos os jogos da fase de grupos foram concluídos
    all_matches_completed = check_all_matches_completed()

    # Filtra os jogos por fase
    group_stage_matches = Match.query.filter_by(phase='fase de grupos').all()
    semi_finals = Match.query.filter_by(phase='semi-final').all()
    final_match = Match.query.filter_by(phase='final').first()  # Apenas um jogo final

    # Combina os jogos das fases para processar os logos
    matches = group_stage_matches + semi_finals
    if final_match:
        matches.append(final_match)

    # Função para formatar o nome do logo
    def format_logo_filename(team_name):
        # Formata o nome do time para o logo
        logo_filename = team_name.strip().replace(" ", "_").replace("-", "_").replace("&", "e").lower()

        # Remove o underscore final, se existir
        if logo_filename.endswith('_'):
            logo_filename = logo_filename[:-1]

        return logo_filename + '.jpg'

    # Processa os logos dos times
    for match in matches:
        for team in [match.team_a, match.team_b]:
            team.logo_filename = format_logo_filename(team.name)

    # Passa as variáveis para o template
    return render_template('matches.html', 
                           group_stage_matches=group_stage_matches,
                           semi_finals=semi_finals,
                           final_match=final_match,
                           all_matches_completed=all_matches_completed)

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

    # Pega todos os jogadores dos dois times
    players_a = Player.query.filter_by(team_id=match.team_a_id).order_by(Player.name).all()
    players_b = Player.query.filter_by(team_id=match.team_b_id).order_by(Player.name).all()

    if request.method == 'POST':
        # 1) Salva o placar da partida
        match.score_a = int(request.form.get('score_a') or 0)
        match.score_b = int(request.form.get('score_b') or 0)

        # 2) Lê os stats por jogador (goals, saves, assists)
        counts_a = {
            p.id: {
                'goals': int(request.form.get(f'goals_a_{p.id}', 0) or 0),
                'saves': int(request.form.get(f'saves_a_{p.id}', 0) or 0),
                'assists': int(request.form.get(f'assists_a_{p.id}', 0) or 0)
            } for p in players_a
        }

        counts_b = {
            p.id: {
                'goals': int(request.form.get(f'goals_b_{p.id}', 0) or 0),
                'saves': int(request.form.get(f'saves_b_{p.id}', 0) or 0),
                'assists': int(request.form.get(f'assists_b_{p.id}', 0) or 0)
            } for p in players_b
        }

        touched_ids = set()

        # Upsert stats do Time A
        for pid, stats in counts_a.items():
            stat = PlayerMatchStat.query.filter_by(match_id=match.id, player_id=pid).first()
            if stats['goals'] == 0 and stats['saves'] == 0 and stats['assists'] == 0:
                if stat:
                    db.session.delete(stat)
            else:
                if not stat:
                    stat = PlayerMatchStat(match_id=match.id, player_id=pid, team_id=match.team_a_id)
                    db.session.add(stat)
                stat.team_id = match.team_a_id
                stat.goals = stats['goals']
                stat.saves = stats['saves']
                stat.assists = stats['assists']
                touched_ids.add(pid)

        # Upsert stats do Time B
        for pid, stats in counts_b.items():
            stat = PlayerMatchStat.query.filter_by(match_id=match.id, player_id=pid).first()
            if stats['goals'] == 0 and stats['saves'] == 0 and stats['assists'] == 0:
                if stat:
                    db.session.delete(stat)
            else:
                if not stat:
                    stat = PlayerMatchStat(match_id=match.id, player_id=pid, team_id=match.team_b_id)
                    db.session.add(stat)
                stat.team_id = match.team_b_id
                stat.goals = stats['goals']
                stat.saves = stats['saves']
                stat.assists = stats['assists']
                touched_ids.add(pid)

        db.session.commit()

        # 3) Atualizar o agregado Player.goals (opcional)
        if touched_ids:
            rows = (
                db.session.query(
                    PlayerMatchStat.player_id,
                    func.coalesce(func.sum(PlayerMatchStat.goals), 0),
                    func.coalesce(func.sum(PlayerMatchStat.saves), 0),
                    func.coalesce(func.sum(PlayerMatchStat.assists), 0)
                )
                .filter(PlayerMatchStat.player_id.in_(touched_ids))
                .group_by(PlayerMatchStat.player_id)
                .all()
            )

            totals = {pid: {'goals': g, 'saves': s, 'assists': a} for pid, g, s, a in rows}
            for player in Player.query.filter(Player.id.in_(touched_ids)).all():
                player.goals = totals.get(player.id, {}).get('goals', 0)
                # Se quiser, você pode adicionar campos agregados de saves/assists no Player
                # player.saves = totals.get(player.id, {}).get('saves', 0)
                # player.assists = totals.get(player.id, {}).get('assists', 0)

            db.session.commit()

        flash('Partida e estatísticas dos jogadores salvos com sucesso.', 'success')
        return redirect(url_for('matches'))

    # GET: pré-preenche os stats existentes para o formulário
    existing = {}
    for s in PlayerMatchStat.query.filter_by(match_id=match.id).all():
        existing[s.player_id] = s.goals
        existing[f"{s.player_id}_saves"] = s.saves
        existing[f"{s.player_id}_assists"] = s.assists

    return render_template(
        'edit_match.html',
        match=match,
        players_a=players_a,
        players_b=players_b,
        stats_by_player=existing
    )

@app.route('/generate_semi_finals', methods=['POST'])
def generate_semi_finals():
    # Garantir que a fase de grupos foi concluída
    if check_all_matches_completed():
        # Obter a classificação
        standings_data = calculate_standings()

        # Gerar as semi-finais com base na classificação
        semi_finals = generate_semi_finals(standings_data)

        # Salve as semi-finais no banco de dados ou qualquer outra lógica necessária
        save_semi_finals(semi_finals)  # Se necessário

        flash('Semi-Finais geradas com sucesso!', 'success')
        return redirect(url_for('standings'))  # Redireciona para a página de classificação
    else:
        flash('Ainda aguardando todos os jogos da fase de grupos serem finalizados.', 'danger')
        return redirect(url_for('standings'))



def build_logo_filename(team_name: str) -> str:
    # Normaliza o nome do time: transforma em minúsculas, substitui espaços por '_', e remove acentos
    logo_filename = (
        team_name
        .strip()  # Remove espaços extras no começo/fim
        .replace(" ", "_")  # Substitui espaços por _
        .replace("-", "_")  # Substitui hífens por _
        .replace("&", "e")  # Substitui o "&" por "e"
        .lower()  # Coloca tudo em minúsculo
    )
    
    # Remove acentos de caracteres
    logo_filename = unidecode.unidecode(logo_filename)  # remove acentos, tipo 'ç', 'á', 'é', etc.

    # Se o nome acabar com um "_" extra, remove
    if logo_filename.endswith('_'):
        logo_filename = logo_filename[:-1]
    
    return logo_filename + '.jpg'  # ou '.png', conforme necessário
if __name__ == '__main__':
    app.run(debug=True)
