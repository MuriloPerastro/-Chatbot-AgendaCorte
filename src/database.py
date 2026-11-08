import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Carrega as variáveis do ficheiro .env localizado na raiz do projeto
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Validação para garantir que as chaves estão configuradas
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "As variáveis SUPABASE_URL e SUPABASE_KEY precisam estar definidas no ficheiro .env!"
    )

# Inicializa e exporta o cliente do Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)