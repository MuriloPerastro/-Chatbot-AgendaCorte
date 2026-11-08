import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Carrega as variáveis do arquivo .env
load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")

# Inicializa o cliente do Supabase
supabase: Client = create_client(url, key)

def testar_conexao():
    try:
        # Busca os profissionais cadastrados no banco
        response = supabase.table("profissionais").select("*").execute()
        print("✅ Conexão bem-sucedida com o Supabase!\n")
        print("Profissionais encontrados no banco:")
        for prof in response.data:
            print(f"- ID: {prof['id']} | Nome: {prof['nome']} | Descrição: {prof['descricao']}")
    except Exception as e:
        print("❌ Erro ao conectar com o Supabase:", e)

if __name__ == "__main__":
    testar_conexao()