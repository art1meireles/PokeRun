"""Pokémon Shiny: um encontro garantido por jornada (em nível sorteado) e,
depois dele, uma pequena chance extra em cada batalha."""

# Faixa de níveis em que o Shiny garantido pode ser sorteado.
NIVEL_MIN_GARANTIDO = 10
NIVEL_MAX_GARANTIDO = 95

# Depois do garantido, cada batalha tem 1 chance em CHANCE_EXTRA de ter um Shiny.
CHANCE_EXTRA = 128

# Multiplicadores do XP da batalha (XP já com bônus de cartas) na recompensa.
MULT_XP = 5
MULT_XP_UNICA_OPCAO = 10  # quando carta e item não podem ser concedidos


class ControleShiny:
    """Decide, a cada batalha, se o oponente é Shiny."""

    def __init__(self, rng, nivel_garantido=None, garantido_ocorreu=False):
        """Sem argumentos extras, sorteia (uma única vez) o nível em que o Shiny
        garantido aparece. Para retomar uma jornada salva, informe o nível já
        sorteado e se o garantido já apareceu."""
        if nivel_garantido is None:
            nivel_garantido = rng.randint(NIVEL_MIN_GARANTIDO, NIVEL_MAX_GARANTIDO)
        self.nivel_garantido = nivel_garantido
        self.garantido_ocorreu = garantido_ocorreu

    def deve_aparecer(self, nivel_jogador: int, rng) -> bool:
        """Chame uma vez por batalha: True se o oponente deve ser Shiny.

        Antes do garantido: só aparece ao chegar ao nível sorteado.
        Depois dele: chance de 1 em CHANCE_EXTRA a cada batalha.
        """
        if not self.garantido_ocorreu:
            if nivel_jogador >= self.nivel_garantido:
                self.garantido_ocorreu = True
                return True
            return False
        return rng.randrange(CHANCE_EXTRA) == 0