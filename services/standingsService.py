# services/standingsService.py

from models import db,Match, Team
from sqlalchemy import func

def calculate_standings():
    """Calcula a classificação geral dos times"""
    teams = Team.query.all()  # Obtém todos os times do banco de dados
    standings_data = []

    for team in teams:
        # Obtenha todas as partidas em que o time participou
        matches_as_team_a = Match.query.filter_by(team_a_id=team.id).all()
        matches_as_team_b = Match.query.filter_by(team_b_id=team.id).all()

        total_matches = 0
        total_goals_scored = 0
        total_goals_against = 0
        goal_difference = 0

        wins = 0
        draws = 0
        losses = 0

        # Contabiliza apenas os jogos finalizados da fase de grupos
        for match in matches_as_team_a:
            if match.score_a is not None and match.score_b is not None:
                total_matches += 1
                total_goals_scored += match.score_a
                total_goals_against += match.score_b
                goal_difference += match.score_a - match.score_b

                if match.score_a > match.score_b:
                    wins += 1
                elif match.score_a == match.score_b:
                    draws += 1
                else:
                    losses += 1

        for match in matches_as_team_b:
            if match.score_a is not None and match.score_b is not None:
                total_matches += 1
                total_goals_scored += match.score_b
                total_goals_against += match.score_a
                goal_difference += match.score_b - match.score_a

                if match.score_b > match.score_a:
                    wins += 1
                elif match.score_a == match.score_b:
                    draws += 1
                else:
                    losses += 1

        points = (wins * 3) + (draws * 1)  # 3 pontos por vitória, 1 ponto por empate

        # Adiciona os dados de cada time na lista
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

    # Ordena a classificação
    standings_data.sort(key=lambda x: (x['points'], x['goal_difference'], x['goals_scored']), reverse=True)

    # Atribui a posição ao time na classificação
    for index, team_data in enumerate(standings_data, start=1):
        team_data['position'] = index

    return standings_data



# Função para gerar as semi-finais
def generate_semi_finals(standings_data):
    """Gera as semi-finais após os jogos da fase de grupos serem concluídos"""
    # Selecionando os 4 primeiros colocados da classificação
    team_1 = standings_data[0]  # 1º colocado
    team_2 = standings_data[1]  # 2º colocado
    team_3 = standings_data[2]  # 3º colocado
    team_4 = standings_data[3]  # 4º colocado

    # Criando os jogos de semi-final
    semi_final_1 = {
        'team_a': team_1['team'],
        'team_b': team_4['team'],
        'winner': None  # Inicia como None, será preenchido após o jogo
    }

    semi_final_2 = {
        'team_a': team_2['team'],
        'team_b': team_3['team'],
        'winner': None  # Inicia como None, será preenchido após o jogo
    }

    # Retornando as semi-finais
    return [semi_final_1, semi_final_2]

def save_semi_finals(standings_data):
    # Pegando os times vencedores da fase de grupos (1º x 4º e 2º x 3º)
    team_1 = standings_data[0]['team']
    team_4 = standings_data[3]['team']
    team_2 = standings_data[1]['team']
    team_3 = standings_data[2]['team']

    # Criando as partidas de semi-final no banco de dados
    semi_final_1 = Match(team_a_id=team_1.id, team_b_id=team_4.id, score_a=None, score_b=None)
    semi_final_2 = Match(team_a_id=team_2.id, team_b_id=team_3.id, score_a=None, score_b=None)

    db.session.add(semi_final_1)
    db.session.add(semi_final_2)
    db.session.commit()



# Função para verificar se todos os jogos foram finalizados
def check_all_matches_completed():
    # Suponhamos que os jogos já realizados da fase anterior estão salvos na tabela `Match`
    completed_matches = Match.query.filter(Match.score_a.isnot(None), Match.score_b.isnot(None)).count()
    
    total_matches_required = 5  # Ou quantos jogos forem necessários para completar a fase
    
    return completed_matches == total_matches_required

