import os
from flask import Flask, flash, render_template, request, redirect, session, url_for
from flask_wtf import CSRFProtect
from sqlalchemy import func
from dotenv import load_dotenv

from models import db, Tournament, Team, Player, Match, PlayerMatchStat
from forms import TournamentForm, TeamForm, PlayerForm, MatchForm
from unidecode import unidecode
from utils import build_logo_filename
from services.standingsService import (
    calculate_standings,
    check_all_matches_completed,
    check_semi_finals_completed,
    generate_semi_finals,
    save_semi_finals,
    generate_final,
    save_final,
)

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-insecure-key-change-me")
app.config["DEBUG"] = os.environ.get("DEBUG", "False").lower() == "true"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///football.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
csrf = CSRFProtect(app)

with app.app_context():
    db.create_all()


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def get_active_tournament():
    """
    Retorna o Tournament ativo (salvo na sessão).
    Fallback: o mais recente do banco.
    """
    tid = session.get("tournament_id")
    if tid:
        t = db.session.get(Tournament, tid)
        if t:
            return t
    return Tournament.query.order_by(Tournament.created_at.desc()).first()


@app.context_processor
def inject_tournament():
    """Disponibiliza active_tournament e tournament_logo em todos os templates."""
    t = get_active_tournament()
    logo = t.logo_filename if t and t.logo_filename else None
    return {"active_tournament": t, "tournament_logo": logo}


def require_tournament():
    """
    Garante que existe um campeonato ativo.
    Use no início de qualquer rota que depende de tournament_id.
    Retorna o Tournament ou None (e já faz flash + redirect internamente).
    """
    t = get_active_tournament()
    if not t:
        flash("Crie um campeonato antes de continuar.", "warning")
    return t


# ──────────────────────────────────────────────────────────────────────────────
# Tournaments
# ──────────────────────────────────────────────────────────────────────────────


@app.route("/")
def index():
    tournaments = Tournament.query.order_by(Tournament.created_at.desc()).all()
    active = get_active_tournament()

    stats = {}
    if active:
        stats["teams"] = Team.query.filter_by(tournament_id=active.id).count()
        stats["matches_played"] = (
            Match.query.filter_by(tournament_id=active.id)
            .filter(Match.score_a.isnot(None))
            .count()
        )
        stats["total_matches"] = Match.query.filter_by(tournament_id=active.id).count()
        stats["total_goals"] = (
            db.session.query(func.coalesce(func.sum(PlayerMatchStat.goals), 0))
            .join(Match, PlayerMatchStat.match_id == Match.id)
            .filter(Match.tournament_id == active.id)
            .scalar()
        )

    return render_template("index.html", tournaments=tournaments, stats=stats)


def _save_logo_tournament(file_storage, tournament_name):
    """Valida e salva o logo do campeonato. Retorna filename ou None."""
    if not file_storage or file_storage.filename == "":
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Formato inválido. Use JPG ou PNG.")
    file_storage.seek(0, 2)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > MAX_LOGO_SIZE:
        raise ValueError("Arquivo muito grande. Máximo permitido: 2 MB.")
    safe_name = tournament_name.strip().lower().replace(" ", "_")
    safe_name = unidecode(safe_name)
    filename = f"tournament_{safe_name}.jpg"
    logos_dir = os.path.join(app.root_path, "static", "logos")
    os.makedirs(logos_dir, exist_ok=True)
    file_storage.save(os.path.join(logos_dir, filename))
    return filename


@app.route("/tournament/new", methods=["GET", "POST"])
def add_tournament():
    form = TournamentForm()
    if form.validate_on_submit():
        try:
            logo_filename = _save_logo_tournament(
                form.logo.data, form.name.data.strip()
            )
        except ValueError as e:
            flash(str(e), "danger")
            return render_template("add_tournament.html", form=form)

        t = Tournament(
            name=form.name.data.strip(),
            edition=form.edition.data.strip() or None,
            logo_filename=logo_filename,
        )
        db.session.add(t)
        db.session.commit()
        session["tournament_id"] = t.id
        flash(f'Campeonato "{t.display_name}" criado e selecionado!', "success")
        return redirect(url_for("index"))
    return render_template("add_tournament.html", form=form)


@app.route("/tournament/select/<int:tid>")
def select_tournament(tid):
    t = Tournament.query.get_or_404(tid)
    session["tournament_id"] = t.id
    flash(f'"{t.display_name}" selecionado.', "success")
    return redirect(url_for("index"))


@app.route("/tournament/finish/<int:tid>", methods=["POST"])
def finish_tournament(tid):
    t = Tournament.query.get_or_404(tid)
    t.status = "finalizado"
    db.session.commit()
    flash(f'Campeonato "{t.display_name}" marcado como finalizado.', "success")
    return redirect(url_for("index"))


# ──────────────────────────────────────────────────────────────────────────────


ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_LOGO_SIZE = 2 * 1024 * 1024  # 2 MB


def _save_logo(file_storage, team_name):
    """Valida e salva o logo. Retorna filename ou None. Lança ValueError se inválido."""
    if not file_storage or file_storage.filename == "":
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Formato inválido. Use JPG ou PNG.")
    file_storage.seek(0, 2)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > MAX_LOGO_SIZE:
        raise ValueError("Arquivo muito grande. Máximo permitido: 2 MB.")
    filename = build_logo_filename(team_name)
    logos_dir = os.path.join(app.root_path, "static", "logos")
    os.makedirs(logos_dir, exist_ok=True)
    file_storage.save(os.path.join(logos_dir, filename))
    return filename


# Teams
# ──────────────────────────────────────────────────────────────────────────────


def get_logo(team):
    """Retorna logo do banco se existir, senão gera pelo nome do time."""
    return team.logo_filename if team.logo_filename else build_logo_filename(team.name)


@app.route("/add_team", methods=["GET", "POST"])
def add_team():
    active = require_tournament()
    if not active:
        return redirect(url_for("add_tournament"))

    form = TeamForm()
    if form.validate_on_submit():
        try:
            logo_filename = _save_logo(form.logo.data, form.name.data.strip())
        except ValueError as e:
            flash(str(e), "danger")
            return render_template("add_team.html", form=form)

        team = Team(
            name=form.name.data.strip(),
            tournament_id=active.id,
            logo_filename=logo_filename,
        )
        db.session.add(team)
        db.session.commit()
        flash("Time adicionado com sucesso!", "success")
        return redirect(url_for("index"))
    return render_template("add_team.html", form=form)


# ──────────────────────────────────────────────────────────────────────────────
# Players
# ──────────────────────────────────────────────────────────────────────────────


@app.route("/players")
def players():
    active = require_tournament()
    if not active:
        return redirect(url_for("add_tournament"))

    teams = Team.query.filter_by(tournament_id=active.id).all()
    for team in teams:
        team.logo_filename = get_logo(team)
    return render_template("players.html", teams=teams)


@app.route("/add_player", methods=["GET", "POST"])
def add_player():
    active = require_tournament()
    if not active:
        return redirect(url_for("add_tournament"))

    form = PlayerForm()
    form.team_id.choices = [
        (t.id, t.name) for t in Team.query.filter_by(tournament_id=active.id).all()
    ]
    if form.validate_on_submit():
        db.session.add(
            Player(
                name=form.name.data.strip(),
                team_id=form.team_id.data,
                position=form.position.data,
                shirt_number=form.shirt_number.data,
            )
        )
        db.session.commit()
        flash("Jogador adicionado com sucesso!", "success")
        return redirect(url_for("players"))
    return render_template("add_player.html", form=form)


@app.route("/edit_player/<int:player_id>", methods=["GET", "POST"])
def edit_player(player_id):
    player = Player.query.get_or_404(player_id)
    active = require_tournament()
    if not active:
        return redirect(url_for("add_tournament"))

    form = PlayerForm()
    form.team_id.choices = [
        (t.id, t.name) for t in Team.query.filter_by(tournament_id=active.id).all()
    ]

    if form.validate_on_submit():
        player.name = form.name.data.strip()
        player.team_id = form.team_id.data
        player.position = form.position.data
        player.shirt_number = form.shirt_number.data
        db.session.commit()
        flash("Jogador atualizado!", "success")
        return redirect(url_for("players"))

    form.name.data = player.name
    form.team_id.data = player.team_id
    form.position.data = player.position
    form.shirt_number.data = player.shirt_number
    return render_template("edit_player.html", form=form, player=player)


# ──────────────────────────────────────────────────────────────────────────────
# Top scorers
# ──────────────────────────────────────────────────────────────────────────────


@app.route("/top_scorers")
def top_scorers():
    active = require_tournament()
    if not active:
        return redirect(url_for("add_tournament"))

    rows = (
        db.session.query(
            Player,
            func.coalesce(func.sum(PlayerMatchStat.goals), 0).label("total_goals"),
            func.coalesce(func.sum(PlayerMatchStat.assists), 0).label("total_assists"),
            func.coalesce(func.sum(PlayerMatchStat.saves), 0).label("total_saves"),
        )
        .join(Team, Player.team_id == Team.id)
        .filter(Team.tournament_id == active.id)
        .outerjoin(PlayerMatchStat, Player.id == PlayerMatchStat.player_id)
        .group_by(Player.id)
        .order_by(func.sum(PlayerMatchStat.goals).desc().nullslast())
        .limit(15)
        .all()
    )

    scorers = [
        {"player": p, "total_goals": g, "total_assists": a, "total_saves": s}
        for p, g, a, s in rows
    ]
    return render_template("top_scorers.html", scorers=scorers)


# ──────────────────────────────────────────────────────────────────────────────
# Matches
# ──────────────────────────────────────────────────────────────────────────────


@app.route("/matches")
def matches():
    active = require_tournament()
    if not active:
        return redirect(url_for("add_tournament"))

    tid = active.id
    group_stage_matches = Match.query.filter_by(
        tournament_id=tid, phase="fase de grupos"
    ).all()
    semi_finals = Match.query.filter_by(tournament_id=tid, phase="semi-final").all()
    final_match = Match.query.filter_by(tournament_id=tid, phase="final").first()

    for m in group_stage_matches + semi_finals + ([final_match] if final_match else []):
        m.team_a.logo_filename = get_logo(m.team_a)
        m.team_b.logo_filename = get_logo(m.team_b)

    return render_template(
        "matches.html",
        group_stage_matches=group_stage_matches,
        semi_finals=semi_finals,
        final_match=final_match,
        all_matches_completed=check_all_matches_completed(tid),
        semi_finals_completed=check_semi_finals_completed(tid),
    )


@app.route("/add_match", methods=["GET", "POST"])
def add_match():
    active = require_tournament()
    if not active:
        return redirect(url_for("add_tournament"))

    form = MatchForm()
    teams = Team.query.filter_by(tournament_id=active.id).all()
    form.team_a_id.choices = [(t.id, t.name) for t in teams]
    form.team_b_id.choices = [(t.id, t.name) for t in teams]

    if form.validate_on_submit():
        db.session.add(
            Match(
                tournament_id=active.id,
                team_a_id=form.team_a_id.data,
                team_b_id=form.team_b_id.data,
                phase=form.phase.data,
            )
        )
        db.session.commit()
        flash("Partida adicionada!", "success")
        return redirect(url_for("matches"))
    return render_template("add_match.html", form=form)


@app.route("/edit_match/<int:match_id>", methods=["GET", "POST"])
def edit_match(match_id):
    match = Match.query.get_or_404(match_id)
    players_a = (
        Player.query.filter_by(team_id=match.team_a_id).order_by(Player.name).all()
    )
    players_b = (
        Player.query.filter_by(team_id=match.team_b_id).order_by(Player.name).all()
    )

    if request.method == "POST":
        match.score_a = int(request.form.get("score_a") or 0)
        match.score_b = int(request.form.get("score_b") or 0)

        def parse_stats(players, side):
            return {
                p.id: {
                    "goals": int(request.form.get(f"goals_{side}_{p.id}", 0) or 0),
                    "saves": int(request.form.get(f"saves_{side}_{p.id}", 0) or 0),
                    "assists": int(request.form.get(f"assists_{side}_{p.id}", 0) or 0),
                }
                for p in players
            }

        team_map = {p.id: match.team_a_id for p in players_a}
        team_map.update({p.id: match.team_b_id for p in players_b})
        all_stats = {**parse_stats(players_a, "a"), **parse_stats(players_b, "b")}

        for pid, stats in all_stats.items():
            stat = PlayerMatchStat.query.filter_by(
                match_id=match.id, player_id=pid
            ).first()
            if all(v == 0 for v in stats.values()):
                if stat:
                    db.session.delete(stat)
            else:
                if not stat:
                    stat = PlayerMatchStat(
                        match_id=match.id, player_id=pid, team_id=team_map[pid]
                    )
                    db.session.add(stat)
                stat.goals = stats["goals"]
                stat.saves = stats["saves"]
                stat.assists = stats["assists"]

        db.session.commit()
        flash("Partida e estatísticas salvas!", "success")
        return redirect(url_for("matches"))

    existing = {}
    for s in PlayerMatchStat.query.filter_by(match_id=match.id).all():
        existing[s.player_id] = s.goals
        existing[f"{s.player_id}_saves"] = s.saves
        existing[f"{s.player_id}_assists"] = s.assists

    return render_template(
        "edit_match.html",
        match=match,
        players_a=players_a,
        players_b=players_b,
        stats_by_player=existing,
    )


@app.route("/match/<int:match_id>")
def match_detail(match_id):
    match = Match.query.get_or_404(match_id)
    match.team_a.logo_filename = get_logo(match.team_a)
    match.team_b.logo_filename = get_logo(match.team_b)

    stats = PlayerMatchStat.query.filter_by(match_id=match.id).all()
    stats_a = [s for s in stats if s.team_id == match.team_a_id]
    stats_b = [s for s in stats if s.team_id == match.team_b_id]

    return render_template(
        "match_detail.html", match=match, stats_a=stats_a, stats_b=stats_b
    )


# ──────────────────────────────────────────────────────────────────────────────
# Standings + geração de fases
# ──────────────────────────────────────────────────────────────────────────────


@app.route("/standings")
def standings():
    active = require_tournament()
    if not active:
        return redirect(url_for("add_tournament"))

    tid = active.id
    standings_data = calculate_standings(tid)
    teams_map = {t.name: t for t in Team.query.filter_by(tournament_id=tid).all()}
    for row in standings_data:
        team_obj = teams_map.get(row["team"])
        row["logo_filename"] = (
            get_logo(team_obj) if team_obj else build_logo_filename(row["team"])
        )

    semi_finals = Match.query.filter_by(tournament_id=tid, phase="semi-final").all()
    final_match = Match.query.filter_by(tournament_id=tid, phase="final").first()

    for m in semi_finals:
        m.team_a.logo_filename = get_logo(m.team_a)
        m.team_b.logo_filename = get_logo(m.team_b)

    if final_match:
        final_match.team_a.logo_filename = get_logo(final_match.team_a)
        final_match.team_b.logo_filename = get_logo(final_match.team_b)

    return render_template(
        "standings.html",
        standings=standings_data,
        semi_finals=semi_finals,
        final_match=final_match,
        all_matches_completed=check_all_matches_completed(tid),
        semi_finals_completed=check_semi_finals_completed(tid),
    )


@app.route("/generate_semi_finals", methods=["POST"])
def generate_semi_finals_route():
    active = require_tournament()
    if not active:
        return redirect(url_for("add_tournament"))

    tid = active.id

    if not check_all_matches_completed(tid):
        flash("Ainda há jogos de grupos não finalizados.", "danger")
        return redirect(url_for("standings"))

    if Match.query.filter_by(tournament_id=tid, phase="semi-final").count() > 0:
        flash("As semi-finais já foram geradas.", "warning")
        return redirect(url_for("standings"))

    data = calculate_standings(tid)
    if len(data) < 4:
        flash("São necessários pelo menos 4 times classificados.", "danger")
        return redirect(url_for("standings"))

    save_semi_finals(generate_semi_finals(data), tid)
    flash("Semi-finais geradas!", "success")
    return redirect(url_for("standings"))


@app.route("/generate_final", methods=["POST"])
def generate_final_route():
    active = require_tournament()
    if not active:
        return redirect(url_for("add_tournament"))

    tid = active.id

    if not check_semi_finals_completed(tid):
        flash("Ainda há semi-finais não finalizadas.", "danger")
        return redirect(url_for("standings"))

    if Match.query.filter_by(tournament_id=tid, phase="final").count() > 0:
        flash("A final já foi gerada.", "warning")
        return redirect(url_for("standings"))

    semis = Match.query.filter_by(tournament_id=tid, phase="semi-final").all()
    final_data = generate_final(semis)

    if final_data is None:
        flash(
            "Não foi possível determinar os finalistas. Verifique os placares.",
            "danger",
        )
        return redirect(url_for("standings"))

    save_final(final_data, tid)
    flash("Final gerada! Boa sorte aos finalistas!", "success")
    return redirect(url_for("standings"))


if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])
