
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client


# Localiza o arquivo .env na raiz do projeto
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


# Recupera as credenciais
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


# Valida as configurações
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "As variáveis SUPABASE_URL e SUPABASE_KEY "
        "precisam estar definidas no arquivo .env!"
    )


# Inicializa a conexão com o Supabase
supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)
