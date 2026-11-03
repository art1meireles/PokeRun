import json
import random
from pathlib import Path

DADOS = Path(__file__).parent / "dados"
MAX_CARTAS = 3
OPCOES_POR_SORTEIO = 3


def carregar_cartas() -> dict:
    """Retorna {id: carta}."""
    with open(DADOS / "cartas.json", encoding="utf-8") as f:
        return {c["id"]: c for c in json.load(f)}


CARTAS = carregar_cartas()


def sortear_opcoes(ja_possui: list, rng=random, quantidade: int = OPCOES_POR_SORTEIO) -> list:
    # Sorteia cartas (ids) que o jogador ainda não possui
    disponiveis = [cid for cid in CARTAS if cid not in ja_possui]
    return rng.sample(disponiveis, min(quantidade, len(disponiveis)))


def bonus_xp_pct(cartas_ids: list, oponente) -> int:
    #Soma (em pontos percentuais) o bônus de XP de todas as cartas aplicáveis contra esse oponente
    total = 0
    for cid in cartas_ids:
        efeito = CARTAS[cid]["efeito"]
        kind = efeito["tipo"]
        if kind == "xp_global":
            total += efeito["bonus_pct"]
        elif kind == "xp_tipo" and efeito["pokemon_tipo"] in oponente.tipos:
            total += efeito["bonus_pct"]
        elif kind == "xp_nivel_minimo" and oponente.nivel >= efeito["nivel_minimo"]:
            total += efeito["bonus_pct"]
    return total