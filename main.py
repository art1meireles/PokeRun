import argparse
import random

import batalha
import cartas as cartas_mod
import experiencia
import itens as itens_mod
import oponentes
import salvamento
import shiny as shiny_mod
from interface import InterfaceConsole
from jogador import Jogador
from perguntas import BancoPerguntas

# Níveis que concedem um item extra (Segunda Chance). Se o jogador já tiver
# o item, nada é concedido (máximo de 1 de cada).
ITENS_POR_NIVEL = {25: "segunda_chance", 50: "segunda_chance", 75: "segunda_chance"}


def _sortear_oferta(jogador, rng):
    """Sorteia as opções de uma oferta de nível: cartas, com pequena chance de
    cada opção ser um item. Retorna uma lista de pares ("carta"|"item", id)."""
    cartas_disp = [c for c in cartas_mod.CARTAS if c not in jogador.cartas]
    itens_disp = itens_mod.disponiveis(jogador.itens)
    opcoes = []
    for _ in range(cartas_mod.OPCOES_POR_SORTEIO):
        quer_item = rng.randrange(100) < itens_mod.CHANCE_ITEM_NA_OFERTA
        if itens_disp and (quer_item or not cartas_disp):
            escolhido = rng.choice(itens_disp)
            itens_disp.remove(escolhido)
            opcoes.append(("item", escolhido))
        elif cartas_disp:
            escolhido = rng.choice(cartas_disp)
            cartas_disp.remove(escolhido)
            opcoes.append(("carta", escolhido))
    return opcoes


def _oferecer_recompensa(jogador, ui, rng):
    #Mostra a oferta de nível e aplica a escolha (carta nova, troca de carta ou item)
    opcoes = _sortear_oferta(jogador, rng)
    if not opcoes:
        return
    escolha = ui.escolher_oferta(opcoes, jogador)
    if escolha is None:
        return
    tipo, ident = opcoes[escolha]
    if tipo == "item":
        jogador.dar_item(ident)
        ui.item_ganho(ident)
    elif len(jogador.cartas) < cartas_mod.MAX_CARTAS:
        jogador.cartas.append(ident)
    else:
        idx = ui.escolher_carta_para_substituir(jogador.cartas)
        jogador.cartas[idx] = ident


def _processar_niveis(jogador, niveis, ui, rng):
    #Efeitos de cada nível conquistado: level up, item de marco e oferta de carta/item
    for nivel in niveis:
        ui.level_up(nivel)
        if nivel in ITENS_POR_NIVEL:
            item = ITENS_POR_NIVEL[nivel]
            if jogador.dar_item(item):
                ui.item_ganho(item)
            else:
                ui.mensagem("Você já possui esse item; o do nível não foi concedido.")
        if nivel % 5 == 0 and nivel < experiencia.NIVEL_MAX:
            _oferecer_recompensa(jogador, ui, rng)


def _recompensa_shiny(jogador, xp_batalha, ui, rng):
    """Recompensa por vencer um Shiny: carta, item ou XP (sorteado entre o que for
    possível). Sem carta nem item possíveis, só XP — e em dobro."""
    cartas_disp = [c for c in cartas_mod.CARTAS if c not in jogador.cartas]
    pode_carta = len(jogador.cartas) < cartas_mod.MAX_CARTAS and bool(cartas_disp)
    itens_disp = itens_mod.disponiveis(jogador.itens)

    tipos = ["xp"] + (["carta"] if pode_carta else []) + (["item"] if itens_disp else [])
    if tipos == ["xp"]:
        tipo, mult = "xp", shiny_mod.MULT_XP_UNICA_OPCAO
    else:
        tipo, mult = rng.choice(tipos), shiny_mod.MULT_XP

    if tipo == "carta":
        ident = rng.choice(cartas_disp)
        jogador.cartas.append(ident)
        ui.recompensa_shiny("carta", ident)
    elif tipo == "item":
        ident = rng.choice(itens_disp)
        jogador.dar_item(ident)
        ui.recompensa_shiny("item", ident)
    else:
        xp = xp_batalha * mult
        ui.recompensa_shiny("xp", xp)
        _processar_niveis(jogador, jogador.ganhar_xp(xp), ui, rng)


def jogar(ui, rng=random, estado=None):
    """Roda uma jornada.

    `estado` (um salvamento.EstadoSalvo) continua uma jornada salva; sem ele,
    começa uma nova, com escolha do Pokémon.

    Retorna True se chegou ao nível 100, False no Game Over e None se o
    jogador salvou e saiu entre duas batalhas.
    """
    banco = BancoPerguntas(rng)
    if estado is None:
        iniciais = [p for p in oponentes.carregar_pokemon() if p.get("inicial")]
        jogador = Jogador(ui.escolher_pokemon(iniciais))
        controle_shiny = shiny_mod.ControleShiny(rng)
    else:
        jogador = Jogador(estado.pokemon, estado.xp, list(estado.cartas), list(estado.itens))
        controle_shiny = shiny_mod.ControleShiny(rng, estado.shiny_nivel, estado.shiny_ocorreu)

    # Uma iteração por batalha, até o nível 100 ou um Game Over.
    while jogador.nivel < experiencia.NIVEL_MAX:
        ui.status_jogador(jogador)

        oponente = oponentes.sortear_oponente(jogador.nivel, rng)
        if controle_shiny.deve_aparecer(jogador.nivel, rng):
            oponente.shiny = True
            ui.shiny_apareceu(oponente)
        resultado = batalha.executar_batalha(jogador, oponente, ui, banco)

        if resultado.vitoria:
            base = experiencia.xp_base(oponente.nivel)
            bonus = cartas_mod.bonus_xp_pct(jogador.cartas, oponente)
            xp = experiencia.aplicar_bonus(base, bonus)
            if oponente.shiny:
                ui.resultado_batalha(resultado, oponente)
                _recompensa_shiny(jogador, xp, ui, rng)
            else:
                ui.resultado_batalha(resultado, oponente, xp)
                _processar_niveis(jogador, jogador.ganhar_xp(xp), ui, rng)
        else:
            ui.resultado_batalha(resultado, oponente)
            # Perder para um Shiny nunca causa Game Over.
            if not oponente.shiny and not resultado.segunda_chance_usada:
                ui.game_over(jogador)
                return False

        # Entre batalhas o jogador pode salvar e sair (não há o que salvar no nível 100).
        if (jogador.nivel < experiencia.NIVEL_MAX
                and ui.entre_batalhas(salvamento.gerar_codigo(jogador, controle_shiny))):
            return None

    ui.vitoria_final(jogador)
    return True


def main():
    #Lê a linha de comando e roda jornadas no console até o jogador parar
    parser = argparse.ArgumentParser(description="Pokémon Quiz Roguelike")
    parser.add_argument("--seed", type=int, help="semente aleatória (para reproduzir partidas)")
    args = parser.parse_args()
    rng = random.Random(args.seed) if args.seed is not None else random.Random()

    ui = InterfaceConsole()
    ui.titulo()
    while True:
        escolha, texto = ui.menu_inicial()
        estado = None
        if escolha == "continuar":
            try:
                estado = salvamento.ler_codigo(texto)
            except salvamento.CodigoInvalido as erro:
                ui.codigo_invalido(str(erro))
                continue
        if jogar(ui, rng, estado) is None:  # salvou e saiu
            print("Até a próxima jornada!")
            break
        if not ui.jogar_novamente():
            print("Até a próxima jornada!")
            break


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nJogo encerrado.")