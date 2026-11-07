import json
from pathlib import Path

DADOS = Path(__file__).parent / "dados"

# Chance (em %) de cada opção de uma oferta de nível ser um item em vez de uma carta.
CHANCE_ITEM_NA_OFERTA = 10

# Itens que o jogador escolhe usar durante a batalha (no máximo 1 por batalha).
# A Segunda Chance não está aqui: ela é oferecida automaticamente após uma derrota.
TIPOS_EM_BATALHA = {"pular", "acerto_garantido", "eliminar_opcoes"}


def carregar_itens() -> dict:
    """Retorna {id: item}."""
    with open(DADOS / "itens.json", encoding="utf-8") as f:
        return {i["id"]: i for i in json.load(f)}


ITENS = carregar_itens()


def tipo_do_efeito(item_id: str) -> str:
    return ITENS[item_id]["efeito"]["tipo"]


def usaveis_em_batalha(itens_ids: list) -> list:
    """Dos itens que o jogador carrega, os que podem ser usados durante uma batalha."""
    return [i for i in itens_ids if tipo_do_efeito(i) in TIPOS_EM_BATALHA]


def disponiveis(ja_possui: list) -> list:
    """Ids dos itens que o jogador ainda não possui."""
    return [i for i in ITENS if i not in ja_possui]