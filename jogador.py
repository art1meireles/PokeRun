# Arquivo responsável pelo jogador

from dataclasses import dataclass, field

import experiencia

NOMES_CONSUMIVEIS = {
    "segunda_chance": "Segunda Chance",
}


@dataclass
class Jogador:
    pokemon: str
    xp: int = 0
    cartas: list = field(default_factory=list)
    consumiveis: dict = field(default_factory=dict)  # começa vazio

    @property
    def nivel(self) -> int:
        return experiencia.nivel_por_xp(self.xp)

    def ganhar_xp(self, quantidade: int) -> list:
        #Soma XP e devolve a lista dos níveis conquistados (em ordem)
        antes = self.nivel
        self.xp += quantidade
        depois = self.nivel
        return list(range(antes + 1, depois + 1))

    def tem_consumivel(self, nome: str) -> bool:
        return self.consumiveis.get(nome, 0) > 0

    def usar_consumivel(self, nome: str) -> None:
        if not self.tem_consumivel(nome):
            raise ValueError(f"Sem {nome} disponível")
        self.consumiveis[nome] -= 1

    def dar_consumivel(self, nome: str, quantidade: int = 1) -> None:
        self.consumiveis[nome] = self.consumiveis.get(nome, 0) + quantidade