from dataclasses import dataclass, field

import experiencia

@dataclass
class Jogador:
    pokemon: str
    xp: int = 0
    cartas: list = field(default_factory=list)
    itens: list = field(default_factory=list)  # ids; no máximo 1 de cada

    @property
    def nivel(self) -> int:
        return experiencia.nivel_por_xp(self.xp)

    def ganhar_xp(self, quantidade: int) -> list:
        """Soma XP e devolve a lista dos níveis conquistados (em ordem)."""
        antes = self.nivel
        self.xp += quantidade
        depois = self.nivel
        return list(range(antes + 1, depois + 1))

    def tem_item(self, nome: str) -> bool:
        return nome in self.itens

    def usar_item(self, nome: str) -> None:
        if not self.tem_item(nome):
            raise ValueError(f"Sem {nome} disponível")
        self.itens.remove(nome)

    def dar_item(self, nome: str) -> bool:
        """Guarda o item. Retorna False (e não faz nada) se o jogador já o possui."""
        if self.tem_item(nome):
            return False
        self.itens.append(nome)
        return True