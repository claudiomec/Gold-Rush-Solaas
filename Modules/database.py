import streamlit as st
import json
import firebase_admin
from firebase_admin import credentials, firestore

@st.cache_resource
def get_db():
    """
    Estabelece conexão com o Firestore (Google Cloud).
    Inclui lógica de auto-reparo para chaves privadas mal formatadas.
    """
    try:
        # Evita inicialização duplicada
        if firebase_admin._apps:
            return firestore.client()
            
        if "firebase" in st.secrets:
            # Carrega configurações (suporta TOML Dict ou JSON String)
            if "text_key" in st.secrets["firebase"]:
                key_dict = json.loads(st.secrets["firebase"]["text_key"])
            else:
                key_dict = dict(st.secrets["firebase"])
            
            # --- SANITIZAÇÃO (AUTO-REPARO) DA CHAVE PRIVADA ---
            if "private_key" in key_dict:
                pk = key_dict["private_key"]
                # Remove cabeçalhos duplicados e sujeira de formatação
                pk = pk.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "")
                pk = pk.replace("\\n", "").replace("\n", "").replace(" ", "").replace("\t", "").replace('"', '').replace("'", "")
                # Reconstrói formato PEM padrão
                key_dict["private_key"] = "-----BEGIN PRIVATE KEY-----\n" + pk + "\n-----END PRIVATE KEY-----"

            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred)
            return firestore.client()
        
        return None
    except Exception as e:
        print(f"Database Connection Error: {e}")
        return None

def create_user(username, password, name, role, modules):
    """Cria um novo documento de usuário na coleção 'users'."""
    db = get_db()
    if not db: 
        return False, "Banco de dados offline."
    try:
        db.collection('users').document(username).set({
            'username': username,
            'password': password,
            'name': name,
            'role': role,
            'modules': modules,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        return True, "Usuário criado com sucesso!"
    except Exception as e:
        return False, f"Erro ao gravar: {str(e)}"

def list_all_users():
    """Retorna lista de dicionários com todos os usuários."""
    db = get_db()
    if not db: 
        return []
    try:
        return [doc.to_dict() for doc in db.collection('users').stream()]
    except:
        return []