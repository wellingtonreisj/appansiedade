from datetime import date

QUOTES = [
    {"author": "Viktor Frankl",    "text": "A última das liberdades humanas é a escolha da atitude perante qualquer situação."},
    {"author": "David Goggins",    "text": "A disciplina é o que te separa de quem você quer ser."},
    {"author": "Viktor Frankl",    "text": "Quem tem um porquê para viver suporta quase qualquer como."},
    {"author": "David Goggins",    "text": "Você pode encolher na segurança ou crescer na dificuldade."},
    {"author": "Viktor Frankl",    "text": "Quando não podemos mais mudar uma situação, somos desafiados a nos mudarmos."},
    {"author": "David Goggins",    "text": "Todo dia que você acorda, você tem uma chance de ser melhor que ontem."},
    {"author": "Viktor Frankl",    "text": "O sucesso, como a felicidade, não pode ser perseguido — ele deve resultar."},
    {"author": "David Goggins",    "text": "Dor é temporária. Desistir é para sempre."},
    {"author": "Wellington",       "text": "A disciplina não é sobre ser perfeito todos os dias. É sobre voltar no dia seguinte."},
    {"author": "David Goggins",    "text": "Se você consegue ver a linha de chegada, você não está correndo rápido o suficiente."},
    {"author": "Viktor Frankl",    "text": "A vida nunca se torna insuportável pelas circunstâncias, mas apenas pela falta de significado."},
    {"author": "Hamilton Helmer",  "text": "Excelência estratégica é a soma de mil pequenas decisões corretas."},
    {"author": "David Goggins",    "text": "Você vai sofrer de qualquer forma. Sofra com propósito."},
    {"author": "Viktor Frankl",    "text": "Entre o estímulo e a resposta há um espaço. Nesse espaço está o nosso poder de escolha."},
]

def get_daily_quote() -> dict:
    idx = date.today().toordinal() % len(QUOTES)
    return QUOTES[idx]
