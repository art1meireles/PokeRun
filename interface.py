# Interface do jogo em texto (teclado e tela)

import cartas as cartas_mod
import experiencia
from oponentes import NOMES_DIFICULDADE
from jogador import NOMES_CONSUMIVEIS

LARGURA = 44


def _linha(char="="):
    return char * LARGURA


class InterfaceConsole:
    """Interface em texto, com entrada pelo teclado."""

    # entrada
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

    # telas
    def mensagem(self, texto: str) -> None:
        print(texto)

    def titulo(self) -> None:
        print(_linha())
        print("      POKERUN".center(LARGURA))
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
        itens = ", ".join(f"{NOMES_CONSUMIVEIS[k]} x{v}" for k, v in jogador.consumiveis.items() if v > 0)
        print(f"Consumíveis: {itens or '(nenhum)'}")
        print(_linha("-"))

    def mostrar_batalha(self, jogador, oponente) -> None:
        print("\n" + _linha())
        print("BATALHA".center(LARGURA))
        print(_linha())
        print(f"Seu Pokémon: {jogador.pokemon}\n")
        print("VS\n")
        print(f"Oponente: {oponente.nome}")
        print(f"Tipo: {oponente.tipo_texto}")
        print(f"Nível: {oponente.nivel}\n")
        print(f"Dificuldade: {NOMES_DIFICULDADE[oponente.dificuldade]}")
        print(_linha())

    def perguntar(self, pergunta, acertos, erros):
        print(f"\nAcertos: {acertos}/3   Erros: {erros}/3")
        print(f"\n{pergunta.texto}")
        for i, op in enumerate(pergunta.opcoes, 1):
            print(f"  {i}. {op}")
        while True:
            texto = self._ler(f"Resposta (1-{len(pergunta.opcoes)}): ")
            if texto.isdigit() and 1 <= int(texto) <= len(pergunta.opcoes):
                return int(texto) - 1
            print("  Opção inválida.")

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
        if resultado.vitoria:
            print(f"★ VITÓRIA contra {oponente.nome}! (+{xp_ganho} XP)")
        elif resultado.segunda_chance_usada:
            print("Segunda Chance usada: a jornada continua (sem XP).")
        else:
            print(f"DERROTA contra {oponente.nome}...")

    def level_up(self, nivel) -> None:
        print(f"\n▲ LEVEL UP! Você chegou ao nível {nivel}!")

    def consumivel_ganho(self, nome) -> None:
        print(f"Você ganhou: {NOMES_CONSUMIVEIS[nome]} x1")

    def escolher_carta(self, opcoes, atuais):
        """Retorna o índice escolhido em `opcoes`, ou None para manter as atuais."""
        print("\n" + _linha())
        print("NOVAS CARTAS".center(LARGURA))
        print(_linha())
        for i, cid in enumerate(opcoes, 1):
            c = cartas_mod.CARTAS[cid]
            print(f"{i}. {c['nome']} — {c['descricao']}")
        cheio = len(atuais) >= cartas_mod.MAX_CARTAS
        if cheio:
            print(f"\nVocê já possui {cartas_mod.MAX_CARTAS} cartas.")
            print("Escolha uma nova carta para substituir ou 0 para manter as atuais.")
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