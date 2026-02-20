#!/usr/bin/env python3
"""
Demo interativo do sistema de agentes.
Simula uma conversa de WhatsApp com o atendente IA.
"""
import sys
sys.path.insert(0, '.')

from src.orchestrator import create_steel_sales_team


def main():
    print("=" * 60)
    print("  POC AGNO - ATENDIMENTO DE VENDAS DE ACO")
    print("  Simulacao de conversa via WhatsApp/Blip")
    print("=" * 60)
    print("Digite 'sair' para encerrar\n")

    team = create_steel_sales_team()

    print("Agente: Ola! Bem-vindo a nossa distribuidora de aco. Como posso ajuda-lo hoje?\n")

    while True:
        try:
            user_input = input("Cliente: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando demo...")
            break

        if user_input.lower() in ["sair", "exit", "quit", ""]:
            print("\nEncerrando demo...")
            break

        try:
            response = team.run(user_input)
            content = response.content if hasattr(response, 'content') else str(response)
            print(f"\nAgente: {content}\n")
            print("-" * 40)
        except Exception as e:
            print(f"\nErro: {e}\n")
            break


if __name__ == "__main__":
    main()
