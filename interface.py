import cartas as cartas_mod
import experiencia
import itens as itens_mod
from oponentes import NOMES_DIFICULDADE

LARGURA = 44


def _linha(char="="):
    return char * LARGURA


class InterfaceConsole:
    """Interface em texto, com entrada pelo teclado."""

    # ---------- entrada ----------
    def _ler(self, prompt: str) -> str:
        return input(prompt).strip()

    def _ler_numero(self, prompt: str, minimo: int, maximo: int) -> int:
        while True:
            texto = self._ler(prompt)
            if texto.isdigit() and minimo <= int(texto) <= maximo:
                return int(texto)
            print(f"  Digite um número entre {minimo} e {maximo}.")

    def _confirmar(self, prompt: str) -> bool:
        while True:
            texto = self._ler(prompt + " (s/n): ").lower()
            if texto in ("s", "sim"):
                return True
            if texto in ("n", "nao", "não"):
                return False

    # ---------- telas ----------
    def mensagem(self, texto: str) -> None:
        print(texto)

    def titulo(self) -> None:
        print(_linha())
        print("      POKÉMON QUIZ ROGUELIKE".center(LARGURA))
        print(_linha())
        print("Responda perguntas e suba até o nível 100!")

    def escolher_pokemon(self, iniciais: list) -> str:
        print(_linha())
        print("ESCOLHA SEU POKÉMON".center(LARGURA))
        print(_linha())
        for i, p in enumerate(iniciais, 1):
            print(f"{i}. {p['nome']}")
        n = self._ler_numero("\nEscolha: ", 1, len(iniciais))
        return iniciais[n - 1]["nome"]

    def status_jogador(self, jogador) -> None:
        nivel = jogador.nivel
        if nivel < experiencia.NIVEL_MAX:
            prox = experiencia.xp_para_nivel(nivel + 1)
            xp_txt = f"{jogador.xp}/{prox} XP"
        else:
            xp_txt = f"{jogador.xp} XP"
        print(_linha("-"))
        print(f"{jogador.pokemon} | Nível {nivel} | {xp_txt}")
        if jogador.cartas:
            nomes = ", ".join(cartas_mod.CARTAS[c]["nome"] for c in jogador.cartas)
            print(f"Cartas: {nomes}")
        else:
            print("Cartas: (nenhuma)")
        itens = ", ".join(itens_mod.ITENS[i]["nome"] for i in jogador.itens)
        print(f"Itens: {itens or '(nenhum)'}")
        print(_linha("-"))

    def mostrar_batalha(self, jogador, oponente) -> None:
        print("\n" + _linha())
        print("BATALHA".center(LARGURA))
        print(_linha())
        print(f"Seu Pokémon: {jogador.pokemon}\n")
        print("VS\n")
        marca = "★ SHINY ★ " if oponente.shiny else ""
        print(f"Oponente: {marca}{oponente.nome}")
        print(f"Tipo: {oponente.tipo_texto}")
        print(f"Nível: {oponente.nivel}\n")
        print(f"Dificuldade: {NOMES_DIFICULDADE[oponente.dificuldade]}")
        print(_linha())

    def perguntar(self, pergunta, acertos, erros, eliminadas=(), itens_usaveis=()):
        """Retorna o índice da resposta, ou None se o jogador digitou 0 (menu de itens)."""
        print(f"\nAcertos: {acertos}/3   Erros: {erros}/3")
        print(f"\n{pergunta.texto}")
        for i, op in enumerate(pergunta.opcoes):
            if i in eliminadas:
                print(f"  {i + 1}. ---")
            else:
                print(f"  {i + 1}. {op}")
        if itens_usaveis:
            print("  0. Itens")
        minimo = 0 if itens_usaveis else 1
        while True:
            texto = self._ler(f"Resposta ({minimo}-{len(pergunta.opcoes)}): ")
            if not texto.isdigit():
                print("  Opção inválida.")
                continue
            n = int(texto)
            if n == 0 and itens_usaveis:
                return None
            if 1 <= n <= len(pergunta.opcoes) and (n - 1) not in eliminadas:
                return n - 1
            print("  Opção inválida.")

    def escolher_item(self, itens_usaveis):
        """Menu de itens. Retorna o id do item escolhido ou None para voltar."""
        print("\nITENS (1 por batalha):")
        for i, ident in enumerate(itens_usaveis, 1):
            item = itens_mod.ITENS[ident]
            print(f"  {i}. {item['nome']} — {item['descricao']}")
        n = self._ler_numero("Item (0 para voltar): ", 0, len(itens_usaveis))
        return None if n == 0 else itens_usaveis[n - 1]

    def item_usado(self, ident) -> None:
        print(f"» Você usou: {itens_mod.ITENS[ident]['nome']}")

    def mostrar_resposta(self, pergunta, acertou) -> None:
        if acertou:
            print("✔ Acertou!")
        else:
            print(f"✘ Errou! Resposta certa: {pergunta.opcoes[pergunta.correta]}")

    def oferecer_segunda_chance(self) -> bool:
        print("\nVocê perdeu a batalha!")
        return self._confirmar("Usar Segunda Chance para evitar o Game Over?")

    def resultado_batalha(self, resultado, oponente, xp_ganho=0) -> None:
        print()
        if resultado.vitoria and oponente.shiny:
            print(f"★ Você derrotou o Shiny {oponente.nome}!")
        elif resultado.vitoria:
            print(f"★ VITÓRIA contra {oponente.nome}! (+{xp_ganho} XP)")
        elif oponente.shiny:
            print(f"O Shiny {oponente.nome} escapou... (sem penalidade)")
        elif resultado.segunda_chance_usada:
            print("Segunda Chance usada: a jornada continua (sem XP).")
        else:
            print(f"DERROTA contra {oponente.nome}...")

    def level_up(self, nivel) -> None:
        print(f"\n▲ LEVEL UP! Você chegou ao nível {nivel}!")

    def item_ganho(self, ident) -> None:
        print(f"Você ganhou: {itens_mod.ITENS[ident]['nome']}")

    def shiny_apareceu(self, oponente) -> None:
        print("\n" + _linha("*"))
        print(f"UM {oponente.nome.upper()} SHINY APARECEU!".center(LARGURA))
        print(_linha("*"))

    def recompensa_shiny(self, tipo, valor) -> None:
        """tipo: "carta" (valor = id), "item" (valor = id) ou "xp" (valor = quantidade)."""
        if tipo == "carta":
            c = cartas_mod.CARTAS[valor]
            print(f"RECOMPENSA SHINY — carta: {c['nome']} — {c['descricao']}")
        elif tipo == "item":
            i = itens_mod.ITENS[valor]
            print(f"RECOMPENSA SHINY — item: {i['nome']} — {i['descricao']}")
        else:
            print(f"RECOMPENSA SHINY — +{valor} XP")

    def escolher_oferta(self, opcoes, jogador):
        """`opcoes`: lista de pares ("carta"|"item", id). Retorna o índice escolhido,
        ou None para manter as cartas atuais (só permitido com as cartas cheias)."""
        print("\n" + _linha())
        print("NOVAS OPÇÕES".center(LARGURA))
        print(_linha())
        for i, (tipo, ident) in enumerate(opcoes, 1):
            if tipo == "carta":
                c = cartas_mod.CARTAS[ident]
                print(f"{i}. [Carta] {c['nome']} — {c['descricao']}")
            else:
                item = itens_mod.ITENS[ident]
                print(f"{i}. [Item] {item['nome']} — {item['descricao']}")
        if len(jogador.cartas) >= cartas_mod.MAX_CARTAS:
            print(f"\nVocê já possui {cartas_mod.MAX_CARTAS} cartas.")
            print("Escolher uma carta substitui uma das atuais; 0 mantém tudo como está.")
            n = self._ler_numero("Escolha: ", 0, len(opcoes))
            return None if n == 0 else n - 1
        n = self._ler_numero("Escolha: ", 1, len(opcoes))
        return n - 1

    def escolher_carta_para_substituir(self, atuais) -> int:
        print("\nQual carta você quer substituir?")
        for i, cid in enumerate(atuais, 1):
            c = cartas_mod.CARTAS[cid]
            print(f"{i}. {c['nome']} — {c['descricao']}")
        return self._ler_numero("Escolha: ", 1, len(atuais)) - 1

    def game_over(self, jogador) -> None:
        print("\n" + _linha())
        print("GAME OVER".center(LARGURA))
        print(_linha())
        print(f"{jogador.pokemon} chegou ao nível {jogador.nivel} com {jogador.xp} XP.")

    def vitoria_final(self, jogador) -> None:
        print("\n" + _linha())
        print("★ NÍVEL 100 ALCANÇADO! ★".center(LARGURA))
        print("JORNADA CONCLUÍDA".center(LARGURA))
        print(_linha())
        print(f"{jogador.pokemon} é um verdadeiro Mestre Pokémon!")

    def jogar_novamente(self) -> bool:
        return self._confirmar("\nJogar novamente?")

    def pausa(self) -> None:
        self._ler("\n[Enter para continuar]")