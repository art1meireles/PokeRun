import argparse
import random

import batalha
import cartas as cartas_mod
import experiencia
import oponentes
from interface import InterfaceConsole
from jogador import Jogador
from perguntas import BancoPerguntas

# Níveis que concedem um consumível extra (Segunda Chance).
CONSUMIVEIS_POR_NIVEL = {50: "segunda_chance"}


def _oferecer_carta(jogador, ui, rng):
    opcoes = cartas_mod.sortear_opcoes(jogador.cartas, rng)
    if not opcoes:
        return
    escolha = ui.escolher_carta(opcoes, jogador.cartas)
    if escolha is None:
        return
    nova = opcoes[escolha]
    if len(jogador.cartas) < cartas_mod.MAX_CARTAS:
        jogador.cartas.append(nova)
    else:
        idx = ui.escolher_carta_para_substituir(jogador.cartas)
        jogador.cartas[idx] = nova


def _processar_niveis(jogador, niveis, ui, rng):
    #Efeitos de cada nível conquistado: level up, consumível de marco e carta
    for nivel in niveis:
        ui.level_up(nivel)
        if nivel in CONSUMIVEIS_POR_NIVEL:
            item = CONSUMIVEIS_POR_NIVEL[nivel]
            jogador.dar_consumivel(item)
            ui.consumivel_ganho(item)
        if nivel % 5 == 0 and nivel < experiencia.NIVEL_MAX:
            _oferecer_carta(jogador, ui, rng)


def jogar(ui, rng=random) -> bool:
    # Roda uma jornada completa. Retorna True se chegou ao nível 100
    iniciais = [p for p in oponentes.carregar_pokemon() if p.get("inicial")]
    jogador = Jogador(ui.escolher_pokemon(iniciais))
    banco = BancoPerguntas(rng)

    while jogador.nivel < experiencia.NIVEL_MAX:
        ui.status_jogador(jogador)

        oponente = oponentes.sortear_oponente(jogador.nivel, rng)
        resultado = batalha.executar_batalha(jogador, oponente, ui, banco)

        if resultado.vitoria:
            base = experiencia.xp_base(oponente.nivel)
            bonus = cartas_mod.bonus_xp_pct(jogador.cartas, oponente)
            xp = experiencia.aplicar_bonus(base, bonus)
            ui.resultado_batalha(resultado, oponente, xp)

            niveis = jogador.ganhar_xp(xp)
            _processar_niveis(jogador, niveis, ui, rng)
        else:
            ui.resultado_batalha(resultado, oponente)
            if not resultado.segunda_chance_usada:
                ui.game_over(jogador)
                return False

        ui.pausa()

    ui.vitoria_final(jogador)
    return True


def main():
    parser = argparse.ArgumentParser(description="Pokémon Quiz Roguelike")
    parser.add_argument("--seed", type=int, help="semente aleatória (para reproduzir partidas)")
    args = parser.parse_args()
    rng = random.Random(args.seed) if args.seed is not None else random.Random()

    ui = InterfaceConsole()
    ui.titulo()
    while True:
        jogar(ui, rng)
        if not ui.jogar_novamente():
            print("Até a próxima jornada!")
            break


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nJogo encerrado.")