import json
import random
from dataclasses import dataclass
from pathlib import Path

from oponentes import DIFICULDADES

DADOS = Path(__file__).parent / "dados"

# Ordem das dificuldades, da mais fácil à mais difícil.
ORDEM = [nome for _, nome in DIFICULDADES]

# Mistura de dificuldades das perguntas de uma batalha: {deslocamento de faixa: peso %}.
# Nas pontas (iniciante/expert) o deslocamento que "sairia" da escala fica na faixa da ponta.
MISTURA_NORMAL = {-1: 40, 0: 50, 1: 10}
MISTURA_SHINY = {0: 60, 1: 20, 2: 20}


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

    def sortear_dificuldade(self, dificuldade_base: str, mistura: dict = MISTURA_NORMAL) -> str:
        """Dificuldade de UMA pergunta de uma batalha, a partir da do oponente
        (veja MISTURA_NORMAL e MISTURA_SHINY)."""
        i = ORDEM.index(dificuldade_base)
        indices = [min(max(i + d, 0), len(ORDEM) - 1) for d in mistura]
        escolhida = self._rng.choices(indices, weights=list(mistura.values()), k=1)[0]
        return ORDEM[escolhida]

    def sortear_eliminadas(self, pergunta: Pergunta, quantidade: int = 2) -> set:
        """Índices de `quantidade` alternativas erradas, para o item Eliminar Opções."""
        erradas = [i for i in range(len(pergunta.opcoes)) if i != pergunta.correta]
        return set(self._rng.sample(erradas, min(quantidade, len(erradas))))

    def proxima(self, dificuldade: str) -> Pergunta:
        """Sorteia uma pergunta da dificuldade, sem repetir até esgotar o
        banco daquela dificuldade (depois o ciclo recomeça)."""
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