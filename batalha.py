from dataclasses import dataclass

import itens as itens_mod
from perguntas import MISTURA_NORMAL, MISTURA_SHINY

ACERTOS_PARA_VENCER = 3
ERROS_PARA_PERDER = 3


@dataclass
class ResultadoBatalha:
    vitoria: bool
    acertos: int
    erros: int
    segunda_chance_usada: bool = False
    item_usado: str = None  # item usado durante a batalha (no máximo 1)


def executar_batalha(jogador, oponente, ui, banco) -> ResultadoBatalha:
    """Roda uma batalha completa.

    Itens: durante a batalha o jogador pode usar no máximo 1 item (Pular,
    Acerto Garantido ou Eliminar Opções). Ao perder, a Segunda Chance evita o
    Game Over (sem XP) — exceto contra um Shiny, que nunca causa Game Over.
    """
    mistura = MISTURA_SHINY if oponente.shiny else MISTURA_NORMAL
    acertos = 0
    erros = 0
    item_usado = None

    ui.mostrar_batalha(jogador, oponente)

    while acertos < ACERTOS_PARA_VENCER and erros < ERROS_PARA_PERDER:
        pergunta = banco.proxima(banco.sortear_dificuldade(oponente.dificuldade, mistura))
        eliminadas = set()
        garantido = False

        # Laço da pergunta atual: o jogador pode abrir o menu de itens (0) antes de responder.
        while True:
            usaveis = [] if item_usado else itens_mod.usaveis_em_batalha(jogador.itens)
            escolha = ui.perguntar(pergunta, acertos, erros, eliminadas, usaveis)
            if escolha is not None:
                break
            item = ui.escolher_item(usaveis)
            if item is None:  # voltou do menu sem usar nada
                continue
            jogador.usar_item(item)
            item_usado = item
            ui.item_usado(item)
            efeito = itens_mod.ITENS[item]["efeito"]
            if efeito["tipo"] == "pular":
                pergunta = banco.proxima(banco.sortear_dificuldade(oponente.dificuldade, mistura))
                eliminadas = set()
            elif efeito["tipo"] == "acerto_garantido":
                garantido = True
                break
            elif efeito["tipo"] == "eliminar_opcoes":
                eliminadas = banco.sortear_eliminadas(pergunta, efeito["quantidade"])

        if garantido:
            acertos += 1
            continue

        acertou = escolha == pergunta.correta
        if acertou:
            acertos += 1
        else:
            erros += 1
        ui.mostrar_resposta(pergunta, acertou)

    vitoria = acertos >= ACERTOS_PARA_VENCER
    usou_segunda_chance = False
    if (not vitoria
            and not oponente.shiny
            and jogador.tem_item("segunda_chance")
            and ui.oferecer_segunda_chance()):
        jogador.usar_item("segunda_chance")
        usou_segunda_chance = True

    return ResultadoBatalha(vitoria, acertos, erros, usou_segunda_chance, item_usado)