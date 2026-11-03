#Fórmulas de XP e nível (seções 5 e 6 do documento)

NIVEL_MAX = 100


def xp_para_nivel(n: int) -> int:
    #XP total necessária para alcançar o nível n: 50 × n × (n − 1)
    return 50 * n * (n - 1)


def nivel_por_xp(xp: int) -> int:
    #Maior nível (até 100) cujo requisito de XP já foi atingido
    nivel = 1
    while nivel < NIVEL_MAX and xp >= xp_para_nivel(nivel + 1):
        nivel += 1
    return nivel


def xp_base(nivel_oponente: int) -> int:
    #XP base da batalha: 50 + 25 × nível do oponente.
    return 50 + 25 * nivel_oponente


def aplicar_bonus(xp: int, bonus_pct: int) -> int:
    #XP final = XP base × (1 + bônus). Usa inteiros para evitar erros de ponto flutuante; valores fracionários são arredondados para baixo
    #(ex.: 1.402,5 -> 1.402).
    return xp * (100 + bonus_pct) // 100