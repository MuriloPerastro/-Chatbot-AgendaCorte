import os
import sys

# Adiciona a raiz do projeto ao path do Python para encontrar a pasta 'src'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database import supabase


def testar_conexao_completa():
  print(
      "🔍 A testar a ligação ao Supabase e a integridade das tabelas do"
      " AgendaCorte...\n"
  )

  # Lista das tabelas principais da nossa arquitetura
  tabelas = ["servicos", "profissionais", "clientes", "agendamentos", "profissional_servicos"]

  for tabela in tabelas:
    try:
      # Faz uma consulta rápida limitando a 1 registo para testar o acesso
      response = supabase.table(tabela).select("*").limit(1).execute()
      print(f"✅ Tabela [ {tabela} ] -> Acessível com sucesso!")
    except Exception as e:
      print(f"❌ Erro ao aceder à tabela [ {tabela} ]: {e}")

  print("\n✨ Teste concluído!")


if __name__ == "__main__":
  testar_conexao_completa()