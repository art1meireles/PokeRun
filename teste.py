"""Teste automático do Pokémon Quiz Roguelike.

Roda em duas etapas, sem precisar digitar nada:

  1. TESTES: confere os dados (JSON) e as regras do jogo (XP, oponentes,
     cartas, perguntas, batalha, segunda chance...).
  2. SIMULAÇÃO: um "jogador robô" joga jornadas completas, com diferentes
     taxas de acerto, e mostra estatísticas (quantos chegam ao nível 100 etc.).

Como usar (dentro da pasta do projeto):

    python teste.py                       # testes + simulação (30 jornadas por robô)
    python teste.py --jornadas 100        # simulação maior
    python teste.py --seed 7              # outra semente (resultados diferentes)
    python teste.py --sem-simulacao       # só os testes
"""

import argparse
import collections
import json
import random
import sys
from pathlib import Path

import batalha
import cartas as cartas_mod
import experiencia
import main
import oponentes
import itens as itens_mod
import perguntas as perguntas_mod
import shiny as shiny_mod
from jogador import Jogador
from oponentes import Oponente
from perguntas import BancoPerguntas

DADOS = Path(__file__).parent / "dados"
DIFICULDADES = ["iniciante", "facil", "intermediario", "dificil", "expert"]
TIPOS_DE_EFEITO = {"xp_global", "xp_tipo", "xp_nivel_minimo"}


# ----------------------------------------------------------------------
# Interface "de mentira": responde sozinha, sem teclado e sem imprimir.
# Funciona porque batalha.py e main.py só chamam métodos de um objeto `ui`
# (não importam se ele é a tela de texto ou um robô).
# ----------------------------------------------------------------------
class InterfaceRobo:
    """Joga sozinho. `precisao` é a chance (0 a 1) de acertar cada pergunta:
    um número único ou um dicionário {dificuldade: chance}."""

    def __init__(self, precisao=1.0, rng=None, usar_segunda_chance=True):
        self.precisao = precisao
        self.rng = rng or random.Random()
        self.usar_segunda_chance = usar_segunda_chance
        self.batalhas = 0
        self.vitorias = 0
        self.por_fase = collections.defaultdict(lambda: [0, 0])  # fase -> [vitórias, batalhas]
        self.segundas_chances = 0
        self.ofertas_de_carta = 0
        self.itens_ganhos = []
        self.mensagens = []
        self.shinies = 0
        self.recompensas_shiny = []
        self.niveis_vistos = []
        self.nivel_final = 1
        self.terminou_em_vitoria = False

    # --- escolhas do jogador ---
    def escolher_pokemon(self, iniciais):
        return iniciais[0]["nome"]

    def perguntar(self, pergunta, acertos, erros, eliminadas=(), itens_usaveis=()):
        p = self.precisao
        if isinstance(p, dict):
            p = p[pergunta.chave[0]]
        if self.rng.random() < p:
            return pergunta.correta
        erradas = [i for i in range(len(pergunta.opcoes))
                   if i != pergunta.correta and i not in eliminadas]
        return self.rng.choice(erradas)

    def escolher_item(self, itens_usaveis):
        return None  # o robô comum nunca abre o menu de itens

    def oferecer_segunda_chance(self):
        return self.usar_segunda_chance

    def escolher_oferta(self, opcoes, jogador):
        self.ofertas_de_carta += 1
        for i, (tipo, _) in enumerate(opcoes):  # prefere carta; senão a primeira opção
            if tipo == "carta":
                return i
        return 0

    def escolher_carta_para_substituir(self, atuais):
        return 0

    # --- telas: só registram o que aconteceu ---
    def resultado_batalha(self, resultado, oponente, xp_ganho=0):
        self.batalhas += 1
        fase = min((self._nivel_atual - 1) // 20, 4)  # 0: 1-20 ... 4: 81-100
        self.por_fase[fase][1] += 1
        if resultado.vitoria:
            self.vitorias += 1
            self.por_fase[fase][0] += 1
        elif resultado.segunda_chance_usada:
            self.segundas_chances += 1

    def level_up(self, nivel):
        self.niveis_vistos.append(nivel)

    def item_ganho(self, nome):
        self.itens_ganhos.append(nome)

    def item_usado(self, nome): pass

    def shiny_apareceu(self, oponente):
        self.shinies += 1

    def recompensa_shiny(self, tipo, valor):
        self.recompensas_shiny.append((tipo, valor))

    def game_over(self, jogador):
        self.nivel_final = jogador.nivel

    def vitoria_final(self, jogador):
        self.nivel_final = jogador.nivel
        self.terminou_em_vitoria = True

    # --- telas que não precisam fazer nada ---
    def titulo(self): pass
    def mensagem(self, texto):
        self.mensagens.append(texto)
    def status_jogador(self, jogador): pass
    def mostrar_batalha(self, jogador, oponente):
        self._nivel_atual = jogador.nivel
    def mostrar_resposta(self, pergunta, acertou): pass
    def pausa(self): pass
    def jogar_novamente(self): return False


class InterfaceRoteirizada(InterfaceRobo):
    """Responde conforme um roteiro: lista de True (acerta) / False (erra)."""

    def __init__(self, roteiro, aceitar_segunda_chance=True):
        super().__init__(usar_segunda_chance=aceitar_segunda_chance)
        self.roteiro = list(roteiro)
        self.pendente = None            # item que o roteiro quer usar agora
        self.itens_usados = []
        self.eliminadas_por_pergunta = []  # alternativas eliminadas em cada pergunta
        self.usaveis_por_pergunta = []     # itens que o menu oferecia em cada pergunta
        self.perguntas_feitas = 0
        self.segunda_chance_oferecida = False

    def perguntar(self, pergunta, acertos, erros, eliminadas=(), itens_usaveis=()):
        # Um texto no roteiro (ex.: "pular") significa "abrir o menu e usar esse item".
        if self.roteiro and isinstance(self.roteiro[0], str):
            assert self.roteiro[0] in itens_usaveis, f"item {self.roteiro[0]} não estava disponível"
            self.pendente = self.roteiro.pop(0)
            self.menu_oferecido = list(itens_usaveis)
            return None
        self.perguntas_feitas += 1
        self.eliminadas_por_pergunta.append(set(eliminadas))
        self.usaveis_por_pergunta.append(list(itens_usaveis))
        acerta = self.roteiro.pop(0)
        if acerta:
            return pergunta.correta
        return (pergunta.correta + 1) % len(pergunta.opcoes)

    def escolher_item(self, itens_usaveis):
        return self.pendente

    def item_usado(self, nome):
        self.itens_usados.append(nome)

    def oferecer_segunda_chance(self):
        self.segunda_chance_oferecida = True
        return self.usar_segunda_chance


# ----------------------------------------------------------------------
# Mini-framework de testes: cada função teste_* é um teste.
# `assert condição, "mensagem"` falha se a condição for falsa.
# ----------------------------------------------------------------------
TESTES = []


def teste(funcao):
    TESTES.append(funcao)
    return funcao


def carregar(nome):
    with open(DADOS / nome, encoding="utf-8") as f:
        return json.load(f)


def oponente_exemplo(nivel=10, tipos=("Água",)):
    return Oponente("Teste", list(tipos), nivel)


# ===== 1. DADOS ======================================================
@teste
def dados_pokemon_estrutura():
    lista = carregar("pokemon.json")
    assert len(lista) > 5, "poucos Pokémon no arquivo"
    for p in lista:
        assert isinstance(p.get("nome"), str) and p["nome"].strip(), f"nome inválido: {p}"
        assert isinstance(p.get("tipos"), list) and 1 <= len(p["tipos"]) <= 2, f"tipos inválidos em {p['nome']}"
        assert all(isinstance(t, str) and t.strip() for t in p["tipos"]), f"tipo vazio em {p['nome']}"


@teste
def dados_pokemon_iniciais():
    iniciais = [p for p in carregar("pokemon.json") if p.get("inicial")]
    assert len(iniciais) >= 1, "nenhum Pokémon inicial (inicial: true)"


@teste
def dados_perguntas_estrutura():
    dados = carregar("perguntas.json")
    assert set(dados) == set(DIFICULDADES), f"dificuldades esperadas {DIFICULDADES}, achei {list(dados)}"
    for dif, lista in dados.items():
        assert lista, f"nenhuma pergunta em '{dif}'"
        for q in lista:
            assert q.get("pergunta", "").strip(), f"pergunta vazia em '{dif}'"
            assert len(q.get("erradas", [])) == 3, f"precisa de 3 erradas: {q.get('pergunta')}"
            ops = [q["resposta"]] + q["erradas"]
            assert len(set(ops)) == 4, f"alternativas repetidas: {q['pergunta']}"


@teste
def dados_perguntas_sem_duplicadas():
    textos = [q["pergunta"] for lista in carregar("perguntas.json").values() for q in lista]
    repetidas = {t for t in textos if textos.count(t) > 1}
    assert not repetidas, f"perguntas repetidas: {sorted(repetidas)}"


@teste
def dados_cartas_estrutura():
    lista = carregar("cartas.json")
    ids = [c["id"] for c in lista]
    assert len(ids) == len(set(ids)), "ids de carta repetidos"
    tipos_existentes = {t for p in carregar("pokemon.json") for t in p["tipos"]}
    for c in lista:
        for campo in ("id", "nome", "descricao", "efeito"):
            assert c.get(campo), f"carta {c.get('id')} sem '{campo}'"
        e = c["efeito"]
        assert e.get("tipo") in TIPOS_DE_EFEITO, f"{c['id']}: efeito '{e.get('tipo')}' não é reconhecido pelo cartas.py"
        assert isinstance(e.get("bonus_pct"), int) and e["bonus_pct"] > 0, f"{c['id']}: bonus_pct inválido"
        if e["tipo"] == "xp_tipo":
            assert e.get("pokemon_tipo") in tipos_existentes, f"{c['id']}: tipo '{e.get('pokemon_tipo')}' não existe no pokemon.json"
        if e["tipo"] == "xp_nivel_minimo":
            assert 1 <= e.get("nivel_minimo", 0) <= 100, f"{c['id']}: nivel_minimo inválido"


@teste
def dados_cartas_suficientes_para_o_jogo():
    # O jogador recebe ofertas a cada 5 níveis; precisa haver cartas para sortear.
    assert len(cartas_mod.CARTAS) >= cartas_mod.OPCOES_POR_SORTEIO + cartas_mod.MAX_CARTAS, "poucas cartas"


# ===== 2. EXPERIÊNCIA ================================================
@teste
def xp_para_nivel_valores_conhecidos():
    assert experiencia.xp_para_nivel(1) == 0
    assert experiencia.xp_para_nivel(2) == 40
    assert experiencia.xp_para_nivel(3) == 120
    assert experiencia.xp_para_nivel(100) == 198000


@teste
def nivel_por_xp_limites():
    assert experiencia.nivel_por_xp(0) == 1
    assert experiencia.nivel_por_xp(39) == 1
    assert experiencia.nivel_por_xp(40) == 2
    assert experiencia.nivel_por_xp(119) == 2
    assert experiencia.nivel_por_xp(120) == 3
    assert experiencia.nivel_por_xp(198000) == 100
    assert experiencia.nivel_por_xp(10**9) == 100, "o nível deve parar em 100"


@teste
def nivel_e_xp_sao_coerentes():
    for n in range(1, 101):
        assert experiencia.nivel_por_xp(experiencia.xp_para_nivel(n)) == n, f"nível {n}"


@teste
def xp_base_e_bonus():
    assert experiencia.xp_base(1) == 75
    assert experiencia.xp_base(49) == 1275
    assert experiencia.aplicar_bonus(1275, 0) == 1275
    assert experiencia.aplicar_bonus(1275, 10) == 1402, "1402,5 deve arredondar para baixo"
    assert experiencia.aplicar_bonus(100, 100) == 200


# ===== 3. OPONENTES ==================================================
@teste
def tabelas_somam_100_por_cento():
    for faixa_jogador, faixas in oponentes.TABELAS:
        assert sum(p for _, p in faixas) == 100, f"pesos de {faixa_jogador} não somam 100"


@teste
def tabelas_cobrem_niveis_1_a_100():
    for n in range(1, 101):
        assert oponentes.tabela_do_jogador(n), f"sem tabela para o nível {n}"
    achou_erro = False
    try:
        oponentes.tabela_do_jogador(101)
    except ValueError:
        achou_erro = True
    assert achou_erro, "nível 101 deveria dar ValueError"


@teste
def dificuldade_nos_limites():
    esperado = {1: "iniciante", 10: "iniciante", 11: "facil", 25: "facil",
                26: "intermediario", 50: "intermediario",
                51: "dificil", 75: "dificil", 76: "expert", 100: "expert"}
    for nivel, dif in esperado.items():
        assert oponentes.dificuldade_por_nivel(nivel) == dif, f"nível {nivel} deveria ser {dif}"


@teste
def sorteio_de_nivel_respeita_as_faixas():
    rng = random.Random(1)
    for nivel_jogador in (1, 10, 11, 25, 26, 50, 51, 75, 76, 100):
        faixas = oponentes.tabela_do_jogador(nivel_jogador)
        menor = min(f[0][0] for f in faixas)
        maior = max(f[0][1] for f in faixas)
        for _ in range(500):
            n = oponentes.sortear_nivel(nivel_jogador, rng)
            assert menor <= n <= maior, f"jogador {nivel_jogador}: nível {n} fora de {menor}-{maior}"


@teste
def sortear_oponente_vem_do_json():
    rng = random.Random(3)
    nomes = {p["nome"] for p in carregar("pokemon.json")}
    for _ in range(200):
        o = oponentes.sortear_oponente(30, rng)
        assert o.nome in nomes and 1 <= o.nivel <= 100 and o.tipos
        assert o.dificuldade in DIFICULDADES


# ===== 4. JOGADOR ====================================================
@teste
def jogador_ganha_xp_e_sobe_de_nivel():
    j = Jogador("Pikachu")
    assert j.nivel == 1
    assert j.ganhar_xp(30) == [] and j.nivel == 1
    assert j.ganhar_xp(100) == [2, 3] and j.nivel == 3
    assert j.ganhar_xp(10**7)[-1] == 100 and j.nivel == 100


@teste
def jogador_itens_maximo_um_de_cada():
    j = Jogador("Eevee")
    assert not j.tem_item("segunda_chance")
    assert j.dar_item("segunda_chance") is True
    assert j.dar_item("segunda_chance") is False, "não pode ter 2 do mesmo item"
    assert j.itens == ["segunda_chance"]
    j.usar_item("segunda_chance")
    assert not j.tem_item("segunda_chance")
    erro = False
    try:
        j.usar_item("segunda_chance")
    except ValueError:
        erro = True
    assert erro, "usar item que não existe deve dar ValueError"


@teste
def jogadores_nao_compartilham_listas():
    a, b = Jogador("A"), Jogador("B")
    a.cartas.append("xp_extra")
    a.dar_item("segunda_chance")
    assert b.cartas == [] and b.itens == [], "listas compartilhadas entre jogadores"


# ===== 5. CARTAS =====================================================
@teste
def bonus_de_carta_global():
    assert cartas_mod.bonus_xp_pct(["xp_extra"], oponente_exemplo()) == 10
    assert cartas_mod.bonus_xp_pct([], oponente_exemplo()) == 0


@teste
def bonus_de_carta_por_tipo():
    agua = oponente_exemplo(tipos=("Água", "Gelo"))
    fogo = oponente_exemplo(tipos=("Fogo",))
    assert cartas_mod.bonus_xp_pct(["especialista_agua"], agua) == 10
    assert cartas_mod.bonus_xp_pct(["especialista_agua"], fogo) == 0, "tipo diferente não deve dar bônus"


@teste
def bonus_de_carta_por_nivel_minimo():
    assert cartas_mod.bonus_xp_pct(["mestre_pokedex"], oponente_exemplo(nivel=50)) == 0
    assert cartas_mod.bonus_xp_pct(["mestre_pokedex"], oponente_exemplo(nivel=51)) == 15


@teste
def bonus_de_cartas_acumulam():
    o = oponente_exemplo(nivel=60, tipos=("Água",))
    assert cartas_mod.bonus_xp_pct(["xp_extra", "especialista_agua", "mestre_pokedex"], o) == 10 + 10 + 15


@teste
def sorteio_de_ofertas_nao_repete_cartas_do_jogador():
    rng = random.Random(5)
    possui = list(cartas_mod.CARTAS)[:3]
    for _ in range(100):
        ofertas = cartas_mod.sortear_opcoes(possui, rng)
        assert len(ofertas) == cartas_mod.OPCOES_POR_SORTEIO and len(set(ofertas)) == len(ofertas)
        assert not set(ofertas) & set(possui), "ofereceu carta que o jogador já tem"


# ===== 6. PERGUNTAS ==================================================
@teste
def perguntas_nao_repetem_ate_esgotar():
    dados = carregar("perguntas.json")
    for dif in DIFICULDADES:
        banco = BancoPerguntas(random.Random(2))
        total = len(dados[dif])
        chaves = [banco.proxima(dif).chave for _ in range(total)]
        assert len(set(chaves)) == total, f"'{dif}' repetiu pergunta antes de esgotar"
        banco.proxima(dif)  # depois de esgotar o ciclo recomeça, sem erro


@teste
def pergunta_tem_resposta_certa_no_indice_certo():
    dados = carregar("perguntas.json")
    banco = BancoPerguntas(random.Random(4))
    for dif in DIFICULDADES:
        for _ in range(len(dados[dif])):
            p = banco.proxima(dif)
            correta = dados[dif][p.chave[1]]["resposta"]
            assert p.opcoes[p.correta] == correta, f"índice da resposta errado: {p.texto}"
            assert len(p.opcoes) == 4


@teste
def mistura_de_dificuldades_respeita_os_pesos_e_as_pontas():
    banco = BancoPerguntas(random.Random(5))
    ordem = perguntas_mod.ORDEM
    for i, base in enumerate(ordem):
        vistas = collections.Counter(banco.sortear_dificuldade(base) for _ in range(20000))
        validas = {ordem[max(i - 1, 0)], base, ordem[min(i + 1, len(ordem) - 1)]}
        assert set(vistas) <= validas, f"{base}: sorteou fora da vizinhança {set(vistas)}"
        assert vistas[base] / 20000 > 0.45, f"{base}: a própria faixa deveria dominar"
    assert set(collections.Counter(banco.sortear_dificuldade("iniciante") for _ in range(2000))) <= {"iniciante", "facil"}
    assert set(collections.Counter(banco.sortear_dificuldade("expert") for _ in range(2000))) <= {"dificil", "expert"}


# ===== 7. BATALHA ====================================================
def rodar_batalha(roteiro, com_segunda_chance=False, aceitar=True, itens=(), oponente=None):
    ui = InterfaceRoteirizada(roteiro, aceitar_segunda_chance=aceitar)
    j = Jogador("Pikachu")
    if com_segunda_chance:
        j.dar_item("segunda_chance")
    for item in itens:
        j.dar_item(item)
    banco = BancoPerguntas(random.Random(1))
    r = batalha.executar_batalha(j, oponente or oponente_exemplo(8), ui, banco)
    return r, ui, j


@teste
def batalha_vence_com_3_acertos():
    r, ui, _ = rodar_batalha([True, True, True])
    assert r.vitoria and (r.acertos, r.erros) == (3, 0) and ui.perguntas_feitas == 3


@teste
def batalha_perde_com_3_erros():
    r, ui, _ = rodar_batalha([False, False, False])
    assert not r.vitoria and (r.acertos, r.erros) == (0, 3) and ui.perguntas_feitas == 3


@teste
def batalha_mistura_de_acertos_e_erros():
    r, ui, _ = rodar_batalha([True, False, True, False, True])
    assert r.vitoria and (r.acertos, r.erros) == (3, 2) and ui.perguntas_feitas == 5
    r, ui, _ = rodar_batalha([False, True, False, True, False])
    assert not r.vitoria and (r.acertos, r.erros) == (2, 3)


@teste
def segunda_chance_evita_game_over():
    r, ui, j = rodar_batalha([False, False, False], com_segunda_chance=True)
    assert not r.vitoria and r.segunda_chance_usada
    assert not j.tem_item("segunda_chance"), "o item deveria ter sido gasto"


@teste
def segunda_chance_recusada_nao_gasta_o_item():
    r, ui, j = rodar_batalha([False, False, False], com_segunda_chance=True, aceitar=False)
    assert not r.segunda_chance_usada and j.tem_item("segunda_chance")


@teste
def sem_item_nao_oferece_segunda_chance():
    r, ui, _ = rodar_batalha([False, False, False])
    assert not ui.segunda_chance_oferecida, "não deveria oferecer sem ter o item"


@teste
def vitoria_nao_gasta_segunda_chance():
    r, ui, j = rodar_batalha([True, True, True], com_segunda_chance=True)
    assert r.vitoria and not ui.segunda_chance_oferecida and j.tem_item("segunda_chance")


# ===== 7b. ITENS EM BATALHA ==========================================
@teste
def dados_itens_estrutura():
    dados = carregar("itens.json")
    ids = [i["id"] for i in dados]
    assert len(ids) == len(set(ids)), "ids de itens repetidos"
    for i in dados:
        assert {"id", "nome", "descricao", "efeito"} <= set(i), f"item incompleto: {i}"
        assert i["efeito"]["tipo"] in {"pular", "acerto_garantido", "eliminar_opcoes", "segunda_chance"}
    assert "segunda_chance" in ids


@teste
def item_pular_nao_conta_acerto_nem_erro():
    r, ui, j = rodar_batalha(["pular", True, True, True], itens=["pular"])
    assert r.vitoria and (r.acertos, r.erros) == (3, 0) and ui.perguntas_feitas == 3
    assert r.item_usado == "pular" and not j.tem_item("pular")


@teste
def item_acerto_garantido_vale_um_acerto():
    r, ui, j = rodar_batalha(["acerto_garantido", True, True], itens=["acerto_garantido"])
    assert r.vitoria and (r.acertos, r.erros) == (3, 0)
    assert ui.perguntas_feitas == 2, "a pergunta do item não deve ser respondida"
    assert not j.tem_item("acerto_garantido")


@teste
def item_eliminar_opcoes_tira_duas_erradas():
    r, ui, j = rodar_batalha(["eliminar_opcoes", True, True, True], itens=["eliminar_opcoes"])
    primeira = ui.eliminadas_por_pergunta[0]
    assert len(primeira) == 2, "deveria eliminar 2 alternativas"
    assert ui.eliminadas_por_pergunta[1:] == [set(), set()], "só vale para a pergunta atual"
    assert r.vitoria and not j.tem_item("eliminar_opcoes")


@teste
def so_um_item_por_batalha():
    r, ui, j = rodar_batalha(["pular", True, True, True], itens=["pular", "acerto_garantido"])
    assert ui.menu_oferecido == ["pular", "acerto_garantido"]
    assert all(u == [] for u in ui.usaveis_por_pergunta), "depois de usar 1 item, o menu some"
    assert j.tem_item("acerto_garantido"), "o segundo item deve ser guardado"


@teste
def item_usado_nao_impede_segunda_chance():
    r, ui, j = rodar_batalha(["pular", False, False, False], com_segunda_chance=True, itens=["pular"])
    assert not r.vitoria and r.segunda_chance_usada and r.item_usado == "pular"


@teste
def segunda_chance_nao_aparece_no_menu_de_batalha():
    r, ui, j = rodar_batalha([True, True, True], com_segunda_chance=True)
    assert ui.usaveis_por_pergunta == [[], [], []]


# ===== 7c. SHINY =====================================================
def shiny_exemplo(nivel=10):
    o = oponente_exemplo(nivel)
    o.shiny = True
    return o


@teste
def mistura_shiny_60_20_20():
    banco = BancoPerguntas(random.Random(8))
    n = 30000
    c = collections.Counter(banco.sortear_dificuldade("facil", perguntas_mod.MISTURA_SHINY) for _ in range(n))
    assert set(c) == {"facil", "intermediario", "dificil"}, f"faixas inesperadas: {set(c)}"
    for faixa, esperado in (("facil", .60), ("intermediario", .20), ("dificil", .20)):
        assert abs(c[faixa] / n - esperado) < 0.02, f"{faixa}: {c[faixa] / n:.1%}"
    topo = {banco.sortear_dificuldade("expert", perguntas_mod.MISTURA_SHINY) for _ in range(500)}
    assert topo == {"expert"}, "na ponta, tudo fica no expert"
    quase = {banco.sortear_dificuldade("dificil", perguntas_mod.MISTURA_SHINY) for _ in range(500)}
    assert quase == {"dificil", "expert"}


@teste
def batalha_contra_shiny_usa_a_mistura_shiny():
    class BancoEspiao(BancoPerguntas):
        def __init__(self, rng):
            super().__init__(rng)
            self.misturas = []
        def sortear_dificuldade(self, base, mistura=perguntas_mod.MISTURA_NORMAL):
            self.misturas.append(mistura)
            return super().sortear_dificuldade(base, mistura)
    for shiny, esperada in ((True, perguntas_mod.MISTURA_SHINY), (False, perguntas_mod.MISTURA_NORMAL)):
        banco = BancoEspiao(random.Random(1))
        o = shiny_exemplo() if shiny else oponente_exemplo()
        batalha.executar_batalha(Jogador("Pikachu"), o, InterfaceRoteirizada([True] * 3), banco)
        assert banco.misturas and all(m is esperada for m in banco.misturas)


@teste
def perder_para_shiny_nao_oferece_nem_gasta_segunda_chance():
    r, ui, j = rodar_batalha([False] * 3, com_segunda_chance=True, oponente=shiny_exemplo())
    assert not r.vitoria and not r.segunda_chance_usada
    assert not ui.segunda_chance_oferecida and j.tem_item("segunda_chance")


@teste
def shiny_garantido_aparece_uma_vez_no_nivel_sorteado():
    for semente in range(300):
        rng = random.Random(semente)
        controle = shiny_mod.ControleShiny(rng)
        assert shiny_mod.NIVEL_MIN_GARANTIDO <= controle.nivel_garantido <= shiny_mod.NIVEL_MAX_GARANTIDO
        for nivel in range(1, controle.nivel_garantido):
            assert not controle.deve_aparecer(nivel, rng), "apareceu antes do nível sorteado"
        assert controle.deve_aparecer(controle.nivel_garantido, rng), "o garantido não apareceu"


@teste
def shiny_extra_depois_do_garantido_tem_chance_de_1_em_128():
    rng = random.Random(3)
    controle = shiny_mod.ControleShiny(rng)
    controle.deve_aparecer(100, rng)  # consome o garantido
    n = 128 * 1000
    vistos = sum(controle.deve_aparecer(50, rng) for _ in range(n))
    assert 850 < vistos < 1150, f"esperava ~1000 em {n}, vieram {vistos}"


@teste
def oferta_mistura_itens_com_pouca_chance_sem_repetir():
    rng = random.Random(6)
    j = Jogador("Pikachu")
    total = itens_ = 0
    for _ in range(3000):
        oferta = main._sortear_oferta(j, rng)
        assert len(oferta) == cartas_mod.OPCOES_POR_SORTEIO and len(set(oferta)) == len(oferta)
        total += len(oferta)
        itens_ += sum(tipo == "item" for tipo, _ in oferta)
    assert 0.06 < itens_ / total < 0.14, f"fração de itens fora do esperado: {itens_ / total:.1%}"
    # nada que o jogador já tenha pode ser oferecido
    j.cartas.append("especialista_agua")
    j.dar_item("pular")
    for _ in range(500):
        for tipo, ident in main._sortear_oferta(j, rng):
            assert ident not in (j.cartas if tipo == "carta" else j.itens)
    # com todos os itens em mãos, só cartas
    for ident in itens_mod.ITENS:
        j.dar_item(ident)
    assert all(tipo == "carta" for _ in range(200) for tipo, _ in main._sortear_oferta(j, rng))


@teste
def recompensa_shiny_so_xp_em_dobro_quando_e_a_unica_opcao():
    ui = InterfaceRobo(rng=random.Random(1))
    j = Jogador("Pikachu")
    j.cartas.extend(list(cartas_mod.CARTAS)[:cartas_mod.MAX_CARTAS])
    for ident in itens_mod.ITENS:
        j.dar_item(ident)
    main._recompensa_shiny(j, 100, ui, random.Random(1))
    assert ui.recompensas_shiny == [("xp", 100 * shiny_mod.MULT_XP_UNICA_OPCAO)]
    assert j.xp == 1000 and len(j.cartas) == cartas_mod.MAX_CARTAS


@teste
def recompensa_shiny_sorteia_entre_o_que_for_possivel():
    # cartas cheias, itens livres: só item ou XP (x5)
    tipos = set()
    for semente in range(60):
        ui = InterfaceRobo(rng=random.Random(semente))
        j = Jogador("Pikachu")
        j.cartas.extend(list(cartas_mod.CARTAS)[:cartas_mod.MAX_CARTAS])
        main._recompensa_shiny(j, 100, ui, random.Random(semente))
        (tipo, valor), = ui.recompensas_shiny
        tipos.add(tipo)
        if tipo == "xp":
            assert valor == 100 * shiny_mod.MULT_XP
        else:
            assert tipo == "item" and len(j.itens) == 1
    assert tipos == {"item", "xp"}
    # sem nada: pode vir carta, item ou XP
    tipos = set()
    for semente in range(90):
        ui = InterfaceRobo(rng=random.Random(semente))
        j = Jogador("Pikachu")
        main._recompensa_shiny(j, 100, ui, random.Random(semente))
        (tipo, valor), = ui.recompensas_shiny
        tipos.add(tipo)
        assert tipo != "carta" or len(j.cartas) == 1
    assert tipos == {"carta", "item", "xp"}


@teste
def perder_todos_os_shinies_nunca_causa_game_over():
    class RoboQueErraShiny(InterfaceRobo):
        contra_shiny = False
        def shiny_apareceu(self, oponente):
            super().shiny_apareceu(oponente)
            self.contra_shiny = True
        def perguntar(self, pergunta, acertos, erros, eliminadas=(), itens_usaveis=()):
            if self.contra_shiny:
                return (pergunta.correta + 1) % len(pergunta.opcoes)
            return super().perguntar(pergunta, acertos, erros, eliminadas, itens_usaveis)
        def resultado_batalha(self, resultado, oponente, xp_ganho=0):
            self.contra_shiny = False
            super().resultado_batalha(resultado, oponente, xp_ganho)
    ui = RoboQueErraShiny(precisao=1.0, rng=random.Random(5), usar_segunda_chance=False)
    venceu = main.jogar(ui, random.Random(5))
    assert venceu and ui.shinies >= 1 and ui.recompensas_shiny == []


# ===== 8. LAÇO PRINCIPAL (main.py) ===================================
@teste
def niveis_dao_cartas_e_segunda_chance():
    ui = InterfaceRobo(rng=random.Random(1))
    j = Jogador("Pikachu")
    main._processar_niveis(j, list(range(2, 101)), ui, random.Random(1))
    # ofertas nos níveis 5, 10, ..., 95 (no 100 não há carta)
    assert ui.ofertas_de_carta == 19, f"esperava 19 ofertas, houve {ui.ofertas_de_carta}"
    assert len(j.cartas) == cartas_mod.MAX_CARTAS, "o jogador não deve passar do máximo de cartas"
    # Níveis 25, 50 e 75 dão Segunda Chance, mas só cabe 1: as outras não são concedidas.
    assert ui.itens_ganhos == ["segunda_chance"] and j.itens == ["segunda_chance"]
    assert len(ui.mensagens) == 2, "esperava 2 avisos de item repetido (níveis 50 e 75)"


@teste
def jornada_perfeita_chega_ao_nivel_100():
    ui = InterfaceRobo(precisao=1.0, rng=random.Random(9))
    venceu = main.jogar(ui, random.Random(9))
    assert venceu and ui.terminou_em_vitoria and ui.nivel_final == 100
    assert ui.shinies >= 1, "todo jornada que passa do nível sorteado encontra ao menos 1 Shiny"
    assert ui.vitorias == ui.batalhas, "robô perfeito não pode perder"


@teste
def jornada_que_so_erra_termina_no_nivel_1():
    ui = InterfaceRobo(precisao=0.0, rng=random.Random(9), usar_segunda_chance=False)
    venceu = main.jogar(ui, random.Random(9))
    assert not venceu and ui.nivel_final == 1 and ui.batalhas == 1


@teste
def mesma_semente_gera_a_mesma_jornada():
    def jornada():
        ui = InterfaceRobo(precisao=0.9, rng=random.Random(11))
        main.jogar(ui, random.Random(11))
        return (ui.batalhas, ui.vitorias, ui.nivel_final)
    assert jornada() == jornada(), "com a mesma semente o resultado deve ser idêntico"


# ----------------------------------------------------------------------
# Execução dos testes
# ----------------------------------------------------------------------
def rodar_testes():
    print("=" * 62)
    print(" TESTES")
    print("=" * 62)
    falhas = 0
    for t in TESTES:
        nome = t.__name__.replace("_", " ")
        try:
            t()
            print(f"  ✔ {nome}")
        except AssertionError as erro:
            falhas += 1
            print(f"  ✘ {nome}\n      -> {erro}")
        except Exception as erro:  # erro inesperado no código do jogo
            falhas += 1
            print(f"  ✘ {nome}\n      -> {type(erro).__name__}: {erro}")
    total = len(TESTES)
    print("-" * 62)
    print(f"  {total - falhas}/{total} testes passaram" + ("" if falhas == 0 else f"  ({falhas} falharam)"))
    return falhas


# ----------------------------------------------------------------------
# Simulação: jornadas completas jogadas por robôs
# ----------------------------------------------------------------------
def simular(precisao, jornadas, semente):
    resultados = []
    for i in range(jornadas):
        rng = random.Random(f"{semente}-{precisao}-{i}")
        ui = InterfaceRobo(precisao=precisao, rng=random.Random(rng.random()))
        main.jogar(ui, rng)
        resultados.append(ui)
    return resultados


def rodar_simulacao(jornadas, semente):
    print()
    print("=" * 62)
    print(f" SIMULAÇÃO  ({jornadas} jornadas por robô, semente {semente})")
    print("=" * 62)
    print("  Cada robô responde certo com a probabilidade indicada e sempre")
    print("  usa a Segunda Chance quando a tem.\n")
    cab = f"  {'Acerto':>6} | {'Chegou ao 100':>13} | {'Nível médio':>11} | {'Batalhas':>8} | {'Seg. Chance':>11}"
    print(cab)
    print("  " + "-" * (len(cab) - 2))
    for precisao in (1.0, 0.95, 0.90, 0.80, 0.60):
        rs = simular(precisao, jornadas, semente)
        venceram = sum(r.terminou_em_vitoria for r in rs)
        nivel_medio = sum(r.nivel_final for r in rs) / len(rs)
        batalhas = sum(r.batalhas for r in rs) / len(rs)
        usos = sum(r.segundas_chances for r in rs) / len(rs)
        print(f"  {precisao:>6.0%} | {venceram:>5}/{jornadas:<7} | {nivel_medio:>11.1f} | {batalhas:>8.0f} | {usos:>11.2f}")
    print("\n  Leitura: 'Batalhas' e 'Seg. Chance' são médias por jornada.")
    rodar_calibragem(jornadas, semente)


# Acerto do robô em cada dificuldade de pergunta (jogador "típico") e metas
# de vitória por fase da jornada (nível do jogador 1-20, 21-40, ...).
ACERTO_POR_DIFICULDADE = {"iniciante": .98, "facil": .92, "intermediario": .80, "dificil": .65, "expert": .50}
METAS_POR_FASE = [.98, .92, .85, .78, .70]


def rodar_calibragem(jornadas, semente):
    print()
    print("=" * 62)
    print(" CALIBRAGEM: taxa de vitória por fase da jornada")
    print("=" * 62)
    print("  Robô com acerto por dificuldade: " +
          ", ".join(f"{k} {v:.0%}" for k, v in ACERTO_POR_DIFICULDADE.items()))
    # Mede batalhas isoladas em cada nível (sem depender de sobreviver até lá).
    n = max(jornadas, 30) * 100
    banco_rng = random.Random(f"cal-{semente}")
    banco = BancoPerguntas(banco_rng)
    ui = InterfaceRobo(precisao=ACERTO_POR_DIFICULDADE, rng=random.Random(banco_rng.random()))
    total = [[0, 0] for _ in range(5)]
    for i in range(n):
        nivel = 1 + i % 100
        jogador = Jogador("Pikachu")
        jogador.ganhar_xp(experiencia.xp_para_nivel(nivel))
        oponente = oponentes.sortear_oponente(nivel, banco_rng)
        r = batalha.executar_batalha(jogador, oponente, ui, banco)
        f = (nivel - 1) // 20
        total[f][1] += 1
        total[f][0] += r.vitoria
    print(f"\n  {n} batalhas simuladas (nível do jogador sorteado de 1 a 100)\n")
    print(f"  {'Fase (nível)':>13} | {'Vitórias':>8} | {'Meta':>5}")
    print("  " + "-" * 34)
    for f in range(5):
        v, b = total[f]
        taxa = v / b if b else 0
        print(f"  {f*20+1:>6}-{f*20+20:<6} | {taxa:>8.1%} | {METAS_POR_FASE[f]:>5.0%}")


def principal():
    parser = argparse.ArgumentParser(description="Testes e simulação do Pokémon Quiz Roguelike")
    parser.add_argument("--jornadas", type=int, default=30, help="jornadas por robô na simulação (padrão 30)")
    parser.add_argument("--seed", type=int, default=42, help="semente da simulação (padrão 42)")
    parser.add_argument("--sem-simulacao", action="store_true", help="roda só os testes")
    args = parser.parse_args()

    falhas = rodar_testes()
    if not args.sem_simulacao:
        rodar_simulacao(args.jornadas, args.seed)
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    principal()