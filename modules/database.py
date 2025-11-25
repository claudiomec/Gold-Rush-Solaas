import streamlit as st
import json
import uuid
import firebase_admin
from firebase_admin import credentials, firestore
from modules.security import hash_password, check_password, is_password_hashed

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
    db = get_db()
    if not db: return False, "Banco Offline.", None
    try:
        # Tenta usar o username como ID para unicidade
        doc_ref = db.collection('users').document(username)
        if doc_ref.get().exists: return False, "Login já existe.", None

        # Hash da senha antes de armazenar
        password_hash = hash_password(password)
        
        token = str(uuid.uuid4())
        doc_ref.set({
            'username': username, 'email': email, 'password': password_hash, 'name': name,
            'role': role, 'modules': modules, 'verified': False, 'verification_token': token,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        return True, "Usuário criado!", token
    except Exception as e: return False, str(e), None

def update_user(current_username, new_email, name, role, modules):
    """
    Atualiza usuário. Se o e-mail mudar, reseta a validação e gera novo token.
    Retorna: (Sucesso, Mensagem, Token ou None)
    """
    db = get_db()
    if not db: return False, "Banco Offline.", None
    
    try:
        users_ref = db.collection('users')
        
        # Busca o documento original pelo username atual
        # Nota: Buscamos por query para garantir, caso o ID seja diferente do username
        query = users_ref.where('username', '==', current_username).stream()
        doc_found = None
        for doc in query:
            doc_found = doc
            break
            
        if not doc_found:
            # Fallback: Tenta buscar pelo ID direto
            doc_ref = users_ref.document(current_username)
            if doc_ref.get().exists: doc_found = doc_ref.get()
            else: return False, "Usuário não encontrado.", None
        
        doc_ref = users_ref.document(doc_found.id)
        current_data = doc_found.to_dict()
        
        updates = {
            'name': name, 'role': role, 'modules': modules,
            'last_updated': firestore.SERVER_TIMESTAMP
        }
        
        token = None
        
        # LÓGICA CRÍTICA: Mudança de E-mail
        if new_email != current_data.get('email'):
            # 1. Verifica se o novo e-mail já existe em outro usuário
            dup_check = users_ref.where('username', '==', new_email).stream()
            for _ in dup_check: return False, "Este novo e-mail já está em uso.", None
            
            # 2. Prepara reset de segurança
            token = str(uuid.uuid4())
            updates['email'] = new_email
            updates['username'] = new_email # Atualiza o login também
            updates['verified'] = False     # Bloqueia acesso
            updates['verification_token'] = token
            
            doc_ref.update(updates)
            return True, "E-mail alterado! Login atualizado. Revalidação necessária.", token
        else:
            # Apenas dados cadastrais, sem resetar segurança
            doc_ref.update(updates)
            return True, "Dados atualizados com sucesso.", None

    except Exception as e:
        return False, f"Erro update: {str(e)}", None

def verify_user_token(token):
    db = get_db()
    if not db: return False, "Erro de conexão."
    try:
        users_ref = db.collection('users')
        query = users_ref.where('verification_token', '==', token).stream()
        doc = next(query, None)
        if doc:
            users_ref.document(doc.id).update({'verified': True, 'verification_token': firestore.DELETE_FIELD})
            return True, f"Conta de {doc.get('name')} ativada!"
        return False, "Token inválido."
    except Exception as e: return False, str(e)

def list_all_users():
    db = get_db()
    if not db: return []
    try: return [doc.to_dict() for doc in db.collection('users').stream()]
    except: return []