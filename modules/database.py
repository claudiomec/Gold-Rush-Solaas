import streamlit as st
import json
import uuid
import firebase_admin
from firebase_admin import credentials, firestore

@st.cache_resource
def get_db():
    """Conecta ao Firestore com auto-reparo de chave."""
    try:
        if firebase_admin._apps: return firestore.client()
        
        if "firebase" in st.secrets:
            if "text_key" in st.secrets["firebase"]:
                key_dict = json.loads(st.secrets["firebase"]["text_key"])
            else:
                key_dict = dict(st.secrets["firebase"])
            
            # Sanitização da Chave
            if "private_key" in key_dict:
                pk = key_dict["private_key"]
                pk = pk.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "")
                pk = pk.replace("\\n", "").replace("\n", "").replace(" ", "").replace("\t", "").replace('"', '').replace("'", "")
                key_dict["private_key"] = "-----BEGIN PRIVATE KEY-----\n" + pk + "\n-----END PRIVATE KEY-----"

            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred)
            return firestore.client()
        return None
    except Exception as e:
        print(f"DB Connection Error: {e}")
        return None

def create_user(username, email, password, name, role, modules):
    """
    Cria usuário com status 'verified: False' e gera token de validação.
    """
    db = get_db()
    if not db: return False, "Banco Offline.", None
    
    try:
        doc_ref = db.collection('users').document(username)
        if doc_ref.get().exists: return False, "Login de usuário já existe.", None

        token = str(uuid.uuid4())

        doc_ref.set({
            'username': username,
            'email': email,
            'password': password,
            'name': name,
            'role': role,
            'modules': modules,
            'verified': False,
            'verification_token': token,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        return True, "Usuário criado! Aguardando validação do e-mail.", token
    except Exception as e:
        return False, f"Erro ao gravar: {str(e)}", None

def update_user(username, name, role, modules):
    """
    Atualiza dados cadastrais de um usuário existente.
    """
    db = get_db()
    if not db: return False, "Banco Offline."
    
    try:
        doc_ref = db.collection('users').document(username)
        if not doc_ref.get().exists:
            return False, "Usuário não encontrado."
            
        doc_ref.update({
            'name': name,
            'role': role,
            'modules': modules,
            'last_updated': firestore.SERVER_TIMESTAMP
        })
        return True, "Dados atualizados com sucesso!"
    except Exception as e:
        return False, f"Erro ao atualizar: {str(e)}"

def verify_user_token(token):
    db = get_db()
    if not db: return False, "Erro de conexão."
    try:
        users_ref = db.collection('users')
        query = users_ref.where('verification_token', '==', token).stream()
        user_doc = None
        for doc in query:
            user_doc = doc
            break
        if user_doc:
            users_ref.document(user_doc.id).update({
                'verified': True,
                'verification_token': firestore.DELETE_FIELD
            })
            return True, f"Sucesso! O usuário {user_doc.get('name')} foi validado e ativado."
        else:
            return False, "Token inválido."
    except Exception as e:
        return False, f"Erro na validação: {str(e)}"

def list_all_users():
    db = get_db()
    if not db: return []
    try: return [doc.to_dict() for doc in db.collection('users').stream()]
    except: return []