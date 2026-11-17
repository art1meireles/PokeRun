#Letras de cada Pokémon inicial, item e carta no código de salvamento (formato: salvamento.py).


# Iniciais: código -> nome em pokemon.json
POKEMON_INICIAIS = {
    "C": "Charmander",
    "S": "Squirtle",
    "B": "Bulbasaur",
    "P": "Pikachu",
    "E": "Eevee",
}

# Itens: código -> id em itens.json (a ordem da tabela é a do código)
ITENS = {
    "P": "pular",
    "A": "acerto_garantido",
    "E": "eliminar_opcoes",
    "S": "segunda_chance",
}

# Cartas: código (3 letras) -> id em cartas.json
CARTAS = {
    "AGU": "especialista_agua",
    "FOG": "especialista_fogo",
    "PLA": "especialista_planta",
    "ELE": "especialista_eletrico",
    "PSI": "especialista_psiquico",
    "TER": "especialista_terrestre",
    "PED": "especialista_pedra",
    "NOR": "especialista_normal",
    "FAN": "especialista_fantasma",
    "DRA": "especialista_dragao",
    "VEN": "especialista_veneno",
    "VOA": "especialista_voador",
    "FAD": "especialista_fada",
    "GEL": "especialista_gelo",
    "LUT": "especialista_lutador",
    "ACO": "especialista_aco",
    "SOM": "especialista_sombrio",
    "INS": "especialista_inseto",
    "XPE": "xp_extra",
    "EST": "estudioso",
    "CON": "conhecimento",
    "MPD": "mestre_pokedex",
    "VET": "veterano",
    "CAC": "cacador_de_elite",
}

# Valores especiais
PREFIXO = "PKRN"
SHINY_JA_APARECEU = "SXX"   # no trecho do Shiny
NENHUM = "0"                # no trecho de cartas ou de itens, quando não há nenhum

# Inversas (id do JSON -> código), para gerar o código
CODIGO_DO_POKEMON = {nome: cod for cod, nome in POKEMON_INICIAIS.items()}
CODIGO_DO_ITEM = {ident: cod for cod, ident in ITENS.items()}
CODIGO_DA_CARTA = {ident: cod for cod, ident in CARTAS.items()}


if __name__ == "__main__":
    # Confere as tabelas contra os JSON (rode ao lado de main.py)
    import json
    from pathlib import Path

    dados = Path(__file__).parent / "dados"
    cartas = {c["id"] for c in json.loads((dados / "cartas.json").read_text(encoding="utf-8"))}
    itens = {i["id"] for i in json.loads((dados / "itens.json").read_text(encoding="utf-8"))}
    pokemon = json.loads((dados / "pokemon.json").read_text(encoding="utf-8"))
    iniciais = {p["nome"] for p in pokemon if p.get("inicial")}

    assert len(CARTAS) == len(set(CARTAS.values())), "carta com dois códigos"
    assert all(len(c) == 3 for c in CARTAS), "código de carta deve ter 3 letras"
    assert all(len(c) == 1 for c in ITENS) and all(len(c) == 1 for c in POKEMON_INICIAIS)
    assert set(CARTAS.values()) == cartas, f"cartas sem código ou código inválido: {set(CARTAS.values()) ^ cartas}"
    assert set(ITENS.values()) == itens, f"itens divergentes: {set(ITENS.values()) ^ itens}"
    assert set(POKEMON_INICIAIS.values()) == iniciais, f"iniciais divergentes: {set(POKEMON_INICIAIS.values()) ^ iniciais}"
    print("OK:", len(CARTAS), "cartas,", len(ITENS), "itens,", len(POKEMON_INICIAIS), "iniciais")