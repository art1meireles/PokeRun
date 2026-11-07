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

    def __init__(self, rng):
        self.nivel_garantido = rng.randint(NIVEL_MIN_GARANTIDO, NIVEL_MAX_GARANTIDO)
        self.garantido_ocorreu = False

    def deve_aparecer(self, nivel_jogador: int, rng) -> bool:
        if not self.garantido_ocorreu:
            if nivel_jogador >= self.nivel_garantido:
                self.garantido_ocorreu = True
                return True
            return False
        return rng.randrange(CHANCE_EXTRA) == 0