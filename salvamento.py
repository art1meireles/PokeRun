import re
from dataclasses import dataclass, field

import cartas as cartas_mod
import codigos
import experiencia
import itens as itens_mod
import oponentes
import shiny as shiny_mod


class CodigoInvalido(Exception):
    pass
    #Texto que não é um código válido (a mensagem diz o motivo)


@dataclass
class EstadoSalvo:
    #Progresso lido de um código

    pokemon: str
    xp: int
    cartas: list = field(default_factory=list)   # ids de cartas.json
    itens: list = field(default_factory=list)    # ids de itens.json
    shiny_nivel: int = None                      # None se já apareceu
    shiny_ocorreu: bool = False

    @property
    def nivel(self) -> int:
        return experiencia.nivel_por_xp(self.xp)


def validar_tabelas() -> None:
    #Confere codigos.py com os JSON ao importar, para falhar logo.
    problemas = []
    if len(set(codigos.CARTAS.values())) != len(codigos.CARTAS):
        problemas.append("há carta com dois códigos em codigos.CARTAS")
    if any(len(c) != 3 for c in codigos.CARTAS):
        problemas.append("código de carta deve ter 3 letras")
    if any(len(c) != 1 for c in codigos.ITENS) or any(len(c) != 1 for c in codigos.POKEMON_INICIAIS):
        problemas.append("código de item e de inicial deve ter 1 letra")
    sem_codigo = set(cartas_mod.CARTAS) - set(codigos.CARTAS.values())
    if sem_codigo:
        problemas.append(f"cartas sem código: {sorted(sem_codigo)}")
    if set(codigos.CARTAS.values()) - set(cartas_mod.CARTAS):
        problemas.append("codigos.CARTAS cita carta que não existe em cartas.json")
    if set(codigos.ITENS.values()) != set(itens_mod.ITENS):
        problemas.append("codigos.ITENS não bate com itens.json")
    iniciais = {p["nome"] for p in oponentes.carregar_pokemon() if p.get("inicial")}
    if set(codigos.POKEMON_INICIAIS.values()) != iniciais:
        problemas.append("codigos.POKEMON_INICIAIS não bate com os iniciais de pokemon.json")
    if problemas:
        raise RuntimeError("Tabelas de códigos inconsistentes: " + "; ".join(problemas))

validar_tabelas()

# Gerar
def gerar_codigo(jogador, controle_shiny) -> str:
    """Código do estado atual (só antes do nível 100)."""
    nivel = jogador.nivel
    if nivel >= experiencia.NIVEL_MAX:
        raise ValueError("a jornada já terminou; não há o que salvar")
    parcial = jogador.xp - experiencia.xp_para_nivel(nivel)

    pokemon = f"{codigos.CODIGO_DO_POKEMON[jogador.pokemon]}{nivel:02d}"
    if controle_shiny.garantido_ocorreu:
        shiny = codigos.SHINY_JA_APARECEU
    else:
        shiny = f"S{controle_shiny.nivel_garantido:02d}"
    cartas = "".join(codigos.CODIGO_DA_CARTA[c] for c in jogador.cartas) or codigos.NENHUM
    itens = "".join(cod for cod, ident in codigos.ITENS.items()
                    if jogador.tem_item(ident)) or codigos.NENHUM
    return "-".join([codigos.PREFIXO, pokemon, shiny, cartas, itens, f"{parcial:04d}"])

# Ler
def _sem_repeticao(blocos: list, o_que: str) -> None:
    repetidos = {b for b in blocos if blocos.count(b) > 1}
    if repetidos:
        raise CodigoInvalido(f"{o_que} repetido(a): {', '.join(sorted(repetidos))}")


def ler_codigo(texto: str) -> EstadoSalvo:
    """Valida o texto e devolve o estado; levanta CodigoInvalido com o motivo.

        Ignora maiúsculas e aceita espaços no lugar de traços."""
    partes = re.sub(r"[\s-]+", "-", texto.strip().upper()).split("-")
    if partes[0] != codigos.PREFIXO:
        raise CodigoInvalido(f"o código deve começar com {codigos.PREFIXO}")
    if len(partes) != 6:
        raise CodigoInvalido(f"esperava 6 trechos separados por traço, encontrei {len(partes)}")
    _, pokemon_nivel, shiny, cartas, itens, parcial = partes

    # Pokémon + nível
    if not re.fullmatch(r"[A-Z][0-9]{2}", pokemon_nivel):
        raise CodigoInvalido(f"trecho do Pokémon e nível inválido: {pokemon_nivel} (ex.: P42)")
    if pokemon_nivel[0] not in codigos.POKEMON_INICIAIS:
        raise CodigoInvalido(f"Pokémon {pokemon_nivel[0]} não existe")
    nivel = int(pokemon_nivel[1:])
    if not 1 <= nivel < experiencia.NIVEL_MAX:
        raise CodigoInvalido(f"o nível deve estar entre 01 e {experiencia.NIVEL_MAX - 1}")

    # Shiny
    if shiny == codigos.SHINY_JA_APARECEU:
        shiny_nivel, shiny_ocorreu = None, True
    elif re.fullmatch(r"S[0-9]{2}", shiny):
        shiny_nivel, shiny_ocorreu = int(shiny[1:]), False
        if not shiny_mod.NIVEL_MIN_GARANTIDO <= shiny_nivel <= shiny_mod.NIVEL_MAX_GARANTIDO:
            raise CodigoInvalido(f"o nível do Shiny deve estar entre "
                                 f"{shiny_mod.NIVEL_MIN_GARANTIDO} e {shiny_mod.NIVEL_MAX_GARANTIDO} "
                                 f"(ou {codigos.SHINY_JA_APARECEU})")
    else:
        raise CodigoInvalido(f"trecho do Shiny inválido: {shiny} (ex.: S67 ou SXX)")

    # Cartas
    lista_cartas = []
    if cartas != codigos.NENHUM:
        if len(cartas) % 3 != 0 or not 3 <= len(cartas) <= 3 * cartas_mod.MAX_CARTAS:
            raise CodigoInvalido("as cartas devem ter 3, 6 ou 9 letras (ou 0 se não houver)")
        blocos = [cartas[i:i + 3] for i in range(0, len(cartas), 3)]
        for bloco in blocos:
            if bloco not in codigos.CARTAS:
                raise CodigoInvalido(f"a carta {bloco} não existe")
        _sem_repeticao(blocos, "carta")
        lista_cartas = [codigos.CARTAS[b] for b in blocos]

    # Itens
    lista_itens = []
    if itens != codigos.NENHUM:
        for letra in itens:
            if letra not in codigos.ITENS:
                raise CodigoInvalido(f"o item {letra} não existe")
        _sem_repeticao(list(itens), "item")
        lista_itens = [ident for cod, ident in codigos.ITENS.items() if cod in itens]

    # XP parcial
    if not re.fullmatch(r"[0-9]{4}", parcial):
        raise CodigoInvalido(f"o XP deve ter 4 dígitos (ex.: 0350), encontrei {parcial}")
    limite = experiencia.xp_para_nivel(nivel + 1) - experiencia.xp_para_nivel(nivel)
    if int(parcial) >= limite:
        raise CodigoInvalido(f"no nível {nivel:02d} o XP parcial deve ser menor que {limite}")

    return EstadoSalvo(
        pokemon=codigos.POKEMON_INICIAIS[pokemon_nivel[0]],
        xp=experiencia.xp_para_nivel(nivel) + int(parcial),
        cartas=lista_cartas,
        itens=lista_itens,
        shiny_nivel=shiny_nivel,
        shiny_ocorreu=shiny_ocorreu,
    )


def ficha(estado: EstadoSalvo) -> list:
    """Estado por extenso: pares (rótulo, texto)."""
    nivel = estado.nivel
    parcial = estado.xp - experiencia.xp_para_nivel(nivel)
    limite = experiencia.xp_para_nivel(nivel + 1) - experiencia.xp_para_nivel(nivel)
    milhar = lambda n: f"{n:,}".replace(",", ".")
    if estado.shiny_ocorreu:
        shiny = "já apareceu"
    else:
        shiny = f"aparece no nível {estado.shiny_nivel}"
    return [
        ("Pokémon", estado.pokemon),
        ("Nível", f"{nivel}  ({milhar(parcial)} / {milhar(limite)} XP)"),
        ("Shiny", shiny),
        ("Cartas", ", ".join(cartas_mod.CARTAS[c]["nome"] for c in estado.cartas) or "(nenhuma)"),
        ("Itens", ", ".join(itens_mod.ITENS[i]["nome"] for i in estado.itens) or "(nenhum)"),
    ]