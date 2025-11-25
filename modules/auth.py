import streamlit as st
from modules.database import get_db
from modules.security import check_password, is_password_hashed

def authenticate(username, password):
    """
    Verifica credenciais e STATUS de verificação do e-mail.
    """
    
    # 1. Tentativa Firestore (Principal)
    db = get_db()
    if db:
        try:
            users_ref = db.collection('users')
            # Busca pelo username (não pela senha, pois agora é hash)
            query = users_ref.where('username', '==', username).stream()
            
            for doc in query:
                user_data = doc.to_dict()
                stored_password = user_data.get('password', '')
                
                # Verifica se a senha está em hash ou texto plano (compatibilidade com usuários antigos)
                if is_password_hashed(stored_password):
                    # Senha está em hash - verifica usando bcrypt
                    if not check_password(password, stored_password):
                        continue  # Senha incorreta, tenta próximo usuário
                else:
                    # Senha antiga em texto plano - verifica diretamente (migração gradual)
                    if stored_password != password:
                        continue  # Senha incorreta
                    # Se senha antiga estiver correta, podemos migrar para hash aqui
                    # (opcional: atualizar para hash no próximo login)
                
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