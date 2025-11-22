import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
import toml # Biblioteca para ler o secrets.toml nativamente

# --- CONFIGURAÇÕES ---
COLLECTION_NAME = "market_data"
SYMBOL_WTI = "CL=F"
SYMBOL_BRL = "BRL=X"
DAYS_BACK = 365 * 5 # Carga inicial de 5 anos

def get_db_connection():
    """
    Conecta ao Firestore lendo do secrets.toml local ou Variável de Ambiente.
    """
    key_dict = None
    
    # 1. Tenta ler do arquivo local .streamlit/secrets.toml
    try:
        # Caminho relativo assumindo que o script roda da raiz do projeto
        secrets_path = ".streamlit/secrets.toml"
        if os.path.exists(secrets_path):
            secrets = toml.load(secrets_path)
            if "firebase" in secrets:
                key_dict = secrets["firebase"]
                # Se estiver aninhado como antigamente (text_key), converte
                if "text_key" in key_dict:
                    import json
                    key_dict = json.loads(key_dict["text_key"])
    except Exception as e:
        print(f"⚠️ Erro ao ler secrets local: {e}")

    # 2. Se não achou, tenta variável de ambiente (para CI/CD futuro)
    if not key_dict and "FIREBASE_CREDENTIALS" in os.environ:
        import json
        key_dict = json.loads(os.environ["FIREBASE_CREDENTIALS"])

    if not key_dict:
        raise Exception("❌ Credenciais não encontradas. Verifique se o arquivo .streamlit/secrets.toml existe e tem a seção [firebase].")

    # --- SANITIZAÇÃO DA CHAVE ---
    # Garante que a chave privada está formatada corretamente
    if "private_key" in key_dict:
        pk = key_dict["private_key"]
        pk = pk.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "")
        pk = pk.replace("\\n", "").replace("\n", "").replace(" ", "").replace("\t", "").replace('"', '').replace("'", "")
        key_dict["private_key"] = "-----BEGIN PRIVATE KEY-----\n" + pk + "\n-----END PRIVATE KEY-----"

    # Conecta ao Firebase
    if not firebase_admin._apps:
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    
    return firestore.client()

def extract_market_data():
    """Baixa dados do Yahoo Finance."""
    print(f"📉 Baixando dados ({DAYS_BACK} dias)...")
    end = datetime.now()
    start = end - timedelta(days=DAYS_BACK)
    
    # Baixa com auto_adjust=True para corrigir problemas de dados
    wti = yf.download(SYMBOL_WTI, start=start, end=end, progress=False, auto_adjust=True)['Close']
    brl = yf.download(SYMBOL_BRL, start=start, end=end, progress=False, auto_adjust=True)['Close']
    
    if wti.empty or brl.empty:
        print("⚠️ Aviso: API do Yahoo retornou vazio. Verifique sua conexão.")
        return pd.DataFrame()
        
    # Unifica os dados
    df = pd.concat([wti, brl], axis=1).dropna()
    df.columns = ['WTI', 'USD_BRL']
    df.index.name = 'Date'
    return df

def transform_data(df):
    """Aplica regras de negócio (Cálculo do Preço Base)."""
    if df.empty: return df
    
    print("wd Processando regras de negócio...")
    # Fórmula Base: WTI * Fator + Spread
    df['PP_FOB_USD'] = (df['WTI'] * 0.014) + 0.35
    
    # Prepara ID para o banco (Data em String)
    df = df.reset_index()
    df['doc_id'] = df['Date'].dt.strftime('%Y-%m-%d')
    return df

def load_to_firestore(db, df):
    """Salva no banco de dados em lotes."""
    if df.empty:
        print("⚠️ Nada para salvar.")
        return

    print(f"💾 Gravando no Firestore ({len(df)} registros)...")
    batch = db.batch()
    count = 0
    total = 0
    
    collection_ref = db.collection(COLLECTION_NAME)
    
    for _, row in df.iterrows():
        doc_ref = collection_ref.document(row['doc_id'])
        
        # Dados a salvar
        data = {
            'date': row['Date'],
            'wti': float(row['WTI']),
            'usd_brl': float(row['USD_BRL']),
            'pp_fob_usd': float(row['PP_FOB_USD']),
            'last_updated': firestore.SERVER_TIMESTAMP
        }
        
        batch.set(doc_ref, data)
        count += 1
        total += 1
        
        # Firestore limita batches a 500 operações
        if count >= 400:
            batch.commit()
            batch = db.batch()
            count = 0
            print(f"   ... {total} registros salvos.")
            
    if count > 0:
        batch.commit()
    print("✅ Carga Completa com Sucesso!")

if __name__ == "__main__":
    try:
        print("========================================")
        print("🤖 INICIANDO ROBÔ ETL")
        print("========================================")
        
        # 1. Conectar ao Banco
        db_client = get_db_connection()
        
        # 2. Extrair Dados
        df_raw = extract_market_data()
        
        # 3. Transformar
        df_clean = transform_data(df_raw)
        
        # 4. Carregar no Banco
        load_to_firestore(db_client, df_clean)
        
    except Exception as e:
        print(f"❌ Erro Fatal: {e}")