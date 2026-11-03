#Banco de perguntas por dificuldade

import json
import random
from dataclasses import dataclass
from pathlib import Path

DADOS = Path(__file__).parent / "dados"


@dataclass
class Pergunta:
    texto: str
    opcoes: list
    correta: int  # índice (0-based) da opção correta em `opcoes`
    dificuldade: str
    chave: tuple  # identificador para evitar repetição


class BancoPerguntas:
    def __init__(self, rng=random):
        with open(DADOS / "perguntas.json", encoding="utf-8") as f:
            self._dados = json.load(f)
        self._rng = rng
        self._usadas = {dif: set() for dif in self._dados}

    def proxima(self, dificuldade: str) -> Pergunta:
        #Sorteia uma pergunta da dificuldade, sem repetir até esgotar obanco daquela dificuldade (depois o ciclo recomeça)
        todas = self._dados[dificuldade]
        restantes = [i for i in range(len(todas)) if i not in self._usadas[dificuldade]]
        if not restantes:
            self._usadas[dificuldade].clear()
            restantes = list(range(len(todas)))
        indice = self._rng.choice(restantes)
        self._usadas[dificuldade].add(indice)

        item = todas[indice]
        opcoes = [item["resposta"]] + list(item["erradas"])
        self._rng.shuffle(opcoes)
        return Pergunta(
            texto=item["pergunta"],
            opcoes=opcoes,
            correta=opcoes.index(item["resposta"]),
            dificuldade=dificuldade,
            chave=(dificuldade, indice),
        )