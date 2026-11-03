#Sorteio de oponentes: faixa de nível, nível exato, tipo e dificuldade

import json
import random
from dataclasses import dataclass
from pathlib import Path

DADOS = Path(__file__).parent / "dados"

TABELAS = [
    ((1, 10), [((1, 5), 25), ((6, 10), 60), ((11, 15), 15)]),
    ((11, 25), [((1, 10), 10), ((11, 25), 55), ((26, 35), 25), ((36, 50), 10)]),
    ((26, 50), [((1, 20), 5), ((21, 35), 15), ((36, 55), 50), ((56, 70), 20), ((71, 100), 10)]),
    ((51, 75), [((1, 30), 5), ((31, 50), 15), ((51, 80), 50), ((81, 90), 20), ((91, 100), 10)]),
    ((76, 100), [((1, 50), 5), ((51, 70), 10), ((71, 90), 50), ((91, 99), 25), ((100, 100), 10)]),
]

# nível do oponente -> dificuldade
DIFICULDADES = [
    (10, "iniciante"),
    (25, "facil"),
    (50, "intermediario"),
    (75, "dificil"),
    (100, "expert"),
]

NOMES_DIFICULDADE = {
    "iniciante": "Iniciante",
    "facil": "Fácil",
    "intermediario": "Intermediário",
    "dificil": "Difícil",
    "expert": "Expert",
}


@dataclass
class Oponente:
    nome: str
    tipos: list
    nivel: int

    @property
    def dificuldade(self) -> str:
        return dificuldade_por_nivel(self.nivel)

    @property
    def tipo_texto(self) -> str:
        return "/".join(self.tipos)


def carregar_pokemon() -> list:
    with open(DADOS / "pokemon.json", encoding="utf-8") as f:
        return json.load(f)


def tabela_do_jogador(nivel_jogador: int) -> list:
    for (minimo, maximo), faixas in TABELAS:
        if minimo <= nivel_jogador <= maximo:
            return faixas
    raise ValueError(f"Nível de jogador inválido: {nivel_jogador}")


def sortear_nivel(nivel_jogador: int, rng=random) -> int:
    #Primeiro sorteia a faixa (com pesos), depois o nível dentro dela
    faixas = tabela_do_jogador(nivel_jogador)
    intervalos = [f[0] for f in faixas]
    pesos = [f[1] for f in faixas]
    minimo, maximo = rng.choices(intervalos, weights=pesos, k=1)[0]
    return rng.randint(minimo, maximo)


def dificuldade_por_nivel(nivel_oponente: int) -> str:
    for limite, nome in DIFICULDADES:
        if nivel_oponente <= limite:
            return nome
    return DIFICULDADES[-1][1]


def sortear_oponente(nivel_jogador: int, rng=random) -> Oponente:
    especie = rng.choice(carregar_pokemon())
    nivel = sortear_nivel(nivel_jogador, rng)
    return Oponente(especie["nome"], list(especie["tipos"]), nivel)