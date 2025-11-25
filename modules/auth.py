import streamlit as st
from modules.database import get_db, hash_password

def authenticate(username, password):
    """
    Verifica credenciais e STATUS de verificação do e-mail.
    """
    
    # 1. Tentativa Firestore (Principal)
    db = get_db()
    if db:
        try:
            users_ref = db.collection('users')
            # Hash da senha para comparar com o banco
            hashed_pw = hash_password(password)
            
            query = users_ref.where('username', '==', username).where('password', '==', hashed_pw).stream()
            
            for doc in query:
                user_data = doc.to_dict()
                
                # --- BLOQUEIO DE SEGURANÇA (KYC) ---
                # Se verified existe e é False, bloqueia o acesso.
                # Se verified não existe (usuários antigos), permite (True).
                is_verified = user_data.get('verified', True)
                
                if is_verified is False:
                    return {"error": "🔒 Conta não verificada. Por favor, clique no link enviado para seu e-mail."}
                
                return user_data
        except Exception as e:
            print(f"Auth Error: {e}")
    
    # 2. Tentativa Secrets (Backup Admin)
    # O Admin de emergência (secrets.toml) sempre entra, pois não tem campo 'verified'
    if "users" in st.secrets and username in st.secrets["users"]:
        if st.secrets["users"][username]["password"] == password:
            data = dict(st.secrets["users"][username])
            if "modules" not in data: data["modules"] = ["Monitor"]
            return data
            
    return None

def logout():
    st.session_state["password_correct"] = False
    st.session_state["user_role"] = None
    st.rerun()