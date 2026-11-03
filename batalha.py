# Batalha de perguntas e respostas. Necessário para ganhar: 3 acertos. Perde ao errar 3 vezes.

from dataclasses import dataclass

ACERTOS_PARA_VENCER = 3
ERROS_PARA_PERDER = 3


@dataclass
class ResultadoBatalha:
    vitoria: bool
    acertos: int
    erros: int
    segunda_chance_usada: bool = False


def executar_batalha(jogador, oponente, ui, banco) -> ResultadoBatalha:
    #Roda uma batalha completa.

    #Consumível: Segunda Chance, ao perder, evita o Game Over (sem XP).
    
    acertos = 0
    erros = 0

    ui.mostrar_batalha(jogador, oponente)

    while acertos < ACERTOS_PARA_VENCER and erros < ERROS_PARA_PERDER:
        pergunta = banco.proxima(oponente.dificuldade)
        escolha = ui.perguntar(pergunta, acertos, erros)

        acertou = escolha == pergunta.correta
        if acertou:
            acertos += 1
        else:
            erros += 1
        ui.mostrar_resposta(pergunta, acertou)

    vitoria = acertos >= ACERTOS_PARA_VENCER
    usou_segunda_chance = False
    if (not vitoria
            and jogador.tem_consumivel("segunda_chance")
            and ui.oferecer_segunda_chance()):
        jogador.usar_consumivel("segunda_chance")
        usou_segunda_chance = True

    return ResultadoBatalha(vitoria, acertos, erros, usou_segunda_chance)