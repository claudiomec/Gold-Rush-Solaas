"""
Módulo de Database - Gerenciamento de dados no Firestore
Responsável por operações de usuários e conexão com banco de dados.
"""
import streamlit as st
import json
import uuid
import re
import logging
import traceback
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
import firebase_admin
from firebase_admin import credentials, firestore
from modules.security import hash_password, check_password, is_password_hashed

# Configuração de logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Tenta importar validação criptográfica (opcional)
try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    logger.warning("cryptography não disponível. Validação de chave privada será básica.")


# ============================================================================
# EXCEÇÕES CUSTOMIZADAS
# ============================================================================

class DatabaseError(Exception):
    """Exceção base para erros do database."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Erro de conexão com o banco."""
    pass


class UserValidationError(DatabaseError):
    """Erro de validação de dados do usuário."""
    pass


class UserNotFoundError(DatabaseError):
    """Usuário não encontrado."""
    pass


class DuplicateUserError(DatabaseError):
    """Usuário duplicado."""
    pass


# ============================================================================
# VALIDAÇÃO E SANITIZAÇÃO
# ============================================================================

def is_valid_email(email: str) -> bool:
    """
    Valida formato de e-mail.
    
    Args:
        email: String com e-mail
        
    Returns:
        True se válido, False caso contrário
    """
    if not email or not isinstance(email, str):
        return False
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))


def clean_private_key_string(key_str: str) -> str:
    """
    Remove caracteres problemáticos da chave privada.
    
    Args:
        key_str: String com a chave privada
        
    Returns:
        String limpa
    """
    if not isinstance(key_str, str):
        key_str = str(key_str)
    
    # Remove caracteres nulos e outros caracteres de controle problemáticos
    # Mantém apenas caracteres imprimíveis, espaços em branco normais, e quebras de linha
    cleaned = ''.join(
        char for char in key_str 
        if ord(char) >= 32 or char in '\n\r\t'
    )
    
    # Remove caracteres nulos explicitamente
    cleaned = cleaned.replace('\x00', '')
    cleaned = cleaned.replace('\ufeff', '')  # Remove BOM se presente
    
    return cleaned


def sanitize_private_key(key_str: str) -> str:
    """
    Sanitiza e valida chave privada do Firebase.
    
    Args:
        key_str: String com a chave privada (pode ter formatação variada)
        
    Returns:
        Chave privada formatada corretamente
        
    Raises:
        ValueError: Se a chave não puder ser validada (apenas em casos críticos)
    """
    if not key_str or not isinstance(key_str, str):
        raise ValueError("Chave privada deve ser uma string não vazia")
    
    # Limpa caracteres problemáticos primeiro
    key_str = clean_private_key_string(key_str)
    
    if not key_str or len(key_str.strip()) < 100:
        raise ValueError("Chave privada está vazia ou muito curta após limpeza")
    
    # Se já está no formato PEM correto, limpa e retorna
    if key_str.strip().startswith("-----BEGIN") and key_str.strip().endswith("-----"):
        # Validação básica: verifica se parece uma chave válida
        cleaned_pem = key_str.strip()
        if len(cleaned_pem) > 500:  # Chave PEM completa tem mais de 500 caracteres
            # Remove caracteres nulos que podem ter sido inseridos
            cleaned_pem = cleaned_pem.replace('\x00', '')
            logger.debug("Chave privada já está no formato PEM")
            return cleaned_pem
    
    # Remove todos os espaços, quebras de linha e caracteres especiais
    cleaned = re.sub(r'[\s\n\r\t"\'\\]', '', key_str)
    
    # Remove caracteres nulos que podem ter sido inseridos
    cleaned = cleaned.replace('\x00', '')
    
    # Remove marcadores de início/fim se existirem
    cleaned = re.sub(r'BEGINPRIVATEKEY|ENDPRIVATEKEY', '', cleaned, flags=re.IGNORECASE)
    
    # Validação básica de tamanho (chave privada RSA tem ~344 caracteres em base64)
    if len(cleaned) < 300:
        raise ValueError("Chave privada parece estar incompleta (muito curta)")
    
    # Formata com quebras de linha a cada 64 caracteres (padrão PEM)
    formatted_key = "-----BEGIN PRIVATE KEY-----\n"
    for i in range(0, len(cleaned), 64):
        formatted_key += cleaned[i:i+64] + "\n"
    formatted_key += "-----END PRIVATE KEY-----"
    
    # Validação criptográfica (se disponível) - completamente opcional, não falha se falhar
    if HAS_CRYPTOGRAPHY:
        try:
            serialization.load_pem_private_key(
                formatted_key.encode('utf-8'),
                password=None,
                backend=default_backend()
            )
            logger.debug("Chave privada validada criptograficamente")
        except Exception as e:
            # Loga o erro mas NÃO falha - permite que o Firebase tente usar a chave
            # O Firebase pode conseguir usar a chave mesmo se a validação criptográfica falhar
            logger.warning(f"Validação criptográfica da chave privada falhou, mas continuando: {e}")
            logger.info("Tentando usar a chave mesmo assim - o Firebase pode conseguir validá-la")
    else:
        # Validação básica sem cryptography
        if not formatted_key.startswith("-----BEGIN PRIVATE KEY-----"):
            raise ValueError("Formato de chave privada inválido")
        if not formatted_key.endswith("-----END PRIVATE KEY-----"):
            raise ValueError("Formato de chave privada inválido")
        logger.debug("Chave privada validada (validação básica)")
    
    return formatted_key


def validate_user_data(
    username: str,
    email: str,
    role: Optional[str] = None,
    modules: Optional[List[str]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Valida dados do usuário antes de salvar.
    
    Args:
        username: Nome de usuário
        email: E-mail
        role: Perfil do usuário (opcional)
        modules: Lista de módulos (opcional)
        
    Returns:
        Tuple[is_valid, error_message]
    """
    # Validação de username
    if not username or len(username) < 3:
        return False, "Username deve ter pelo menos 3 caracteres"
    
    if not username.replace('_', '').replace('.', '').replace('-', '').isalnum():
        return False, "Username contém caracteres inválidos (use apenas letras, números, _, ., -)"
    
    # Validação de email
    if not is_valid_email(email):
        return False, "Email inválido"
    
    # Validação de role (se fornecido)
    if role is not None:
        valid_roles = ['client', 'admin']
        if role not in valid_roles:
            return False, f"Role inválida. Permitidas: {valid_roles}"
    
    # Validação de modules (se fornecido)
    if modules is not None:
        valid_modules = ['Monitor', 'Calculadora Financeira', 'Dashboard']
        invalid_modules = [m for m in modules if m not in valid_modules]
        if invalid_modules:
            return False, f"Módulos inválidos: {invalid_modules}. Válidos: {valid_modules}"
    
    return True, None


# ============================================================================
# CONEXÃO COM BANCO
# ============================================================================

@st.cache_resource
def get_db() -> Optional[firestore.Client]:
    """
    Conecta ao Firestore com auto-reparo de chave e validação.
    
    Returns:
        Cliente Firestore ou None se não conseguir conectar
        
    Raises:
        DatabaseConnectionError: Se houver erro crítico de conexão
    """
    try:
        # Se já inicializado, retorna cliente existente
        if firebase_admin._apps:
            logger.debug("Firebase já inicializado, retornando cliente existente")
            return firestore.client()
        
        # Verifica se secrets estão disponíveis
        if "firebase" not in st.secrets:
            logger.warning("Secrets do Firebase não encontrados")
            return None
        
        # Carrega credenciais
        firebase_secrets = st.secrets["firebase"]
        
        if "text_key" in firebase_secrets:
            key_dict = json.loads(firebase_secrets["text_key"])
        else:
            key_dict = dict(firebase_secrets)
        
        # Sanitiza e valida chave privada
        if "private_key" in key_dict:
            try:
                key_dict["private_key"] = sanitize_private_key(key_dict["private_key"])
                logger.info("Chave privada sanitizada e validada com sucesso")
            except ValueError as e:
                logger.error(f"Erro ao sanitizar chave privada: {e}")
                # Tenta usar a chave original mesmo assim - pode funcionar
                logger.warning("Tentando usar a chave privada sem sanitização completa...")
                # Limpa caracteres problemáticos da chave original e tenta usar
                original_key = key_dict["private_key"]
                if isinstance(original_key, str):
                    # Limpa caracteres problemáticos
                    key_dict["private_key"] = clean_private_key_string(original_key).strip()
                    logger.info("Chave privada limpa (caracteres problemáticos removidos)")
                # Continua tentando inicializar o Firebase mesmo com a chave não validada
        
        # Inicializa Firebase
        try:
            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase inicializado com sucesso")
            return firestore.client()
        except Exception as init_error:
            logger.error(f"Erro ao inicializar Firebase: {init_error}")
            return None
    except Exception as e:
        logger.error(
            "Erro ao conectar ao Firestore",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            },
            exc_info=True
        )
        return None


# ============================================================================
# OPERAÇÕES DE USUÁRIO COM TRANSAÇÕES
# ============================================================================

def create_user(
    username: str,
    email: str,
    password: str,
    name: str,
    role: str,
    modules: List[str]
) -> Tuple[bool, str, Optional[str]]:
    """
    Cria novo usuário com transação atômica e validações.
    
    Args:
        username: Nome de usuário (único)
        email: E-mail do usuário
        password: Senha em texto plano
        name: Nome completo
        role: Perfil ('client' ou 'admin')
        modules: Lista de módulos permitidos
        
    Returns:
        Tuple[sucesso, mensagem, token_verificação]
    """
    start_time = datetime.now()
    logger.info(
        "create_user_started",
        extra={
            "username": username,
            "email": email,
            "role": role
        }
    )
    
    db = get_db()
    if not db:
        logger.error("create_user_failed: Banco offline")
        return False, "Banco Offline.", None
    
    # Validação de dados
    is_valid, error_msg = validate_user_data(username, email, role, modules)
    if not is_valid:
        logger.warning(f"create_user_validation_failed: {error_msg}")
        return False, error_msg, None
    
    try:
        # Transação atômica
        transaction = db.transaction()
        
        @firestore.transactional
        def create_user_transaction(transaction):
            """Função transacional para criar usuário."""
            users_ref = db.collection('users')
            
            # Verifica se username já existe (na transação)
            doc_ref = users_ref.document(username)
            snapshot = doc_ref.get(transaction=transaction)
            
            if snapshot.exists:
                raise DuplicateUserError("Login já existe.")
            
            # Verifica se email já existe (na transação)
            email_query = users_ref.where('email', '==', email).limit(1)
            email_docs = list(email_query.stream(transaction=transaction))
            if email_docs:
                raise DuplicateUserError("Email já cadastrado.")
            
            # Hash da senha
            password_hash = hash_password(password)
            
            # Gera token de verificação
            token = str(uuid.uuid4())
            
            # Cria documento
            user_data = {
                'username': username,
                'email': email,
                'password': password_hash,
                'name': name,
                'role': role,
                'modules': modules,
                'verified': False,
                'verification_token': token,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            transaction.set(doc_ref, user_data)
            logger.debug(f"Usuário {username} preparado para criação na transação")
            
            return token
        
        # Executa transação
        token = create_user_transaction(transaction)
        
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(
            "create_user_success",
            extra={
                "username": username,
                "duration_ms": duration_ms
            }
        )
        
        return True, "Usuário criado!", token
        
    except DuplicateUserError as e:
        logger.warning(f"create_user_duplicate: {str(e)}")
        return False, str(e), None
    except Exception as e:
        logger.error(
            "create_user_error",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            },
            exc_info=True
        )
        return False, f"Erro ao criar usuário: {str(e)}", None


def update_user(
    current_username: str,
    new_email: str,
    name: str,
    role: str,
    modules: List[str]
) -> Tuple[bool, str, Optional[str]]:
    """
    Atualiza usuário com transação atômica.
    Se o e-mail mudar, reseta a validação e gera novo token.
    
    Args:
        current_username: Username atual do usuário
        new_email: Novo e-mail (pode ser o mesmo)
        name: Nome completo
        role: Perfil
        modules: Lista de módulos
        
    Returns:
        Tuple[sucesso, mensagem, token_verificação ou None]
    """
    start_time = datetime.now()
    logger.info(
        "update_user_started",
        extra={
            "current_username": current_username,
            "new_email": new_email
        }
    )
    
    db = get_db()
    if not db:
        logger.error("update_user_failed: Banco offline")
        return False, "Banco Offline.", None
    
    # Validação de dados
    is_valid, error_msg = validate_user_data(current_username, new_email, role, modules)
    if not is_valid:
        logger.warning(f"update_user_validation_failed: {error_msg}")
        return False, error_msg, None
    
    try:
        # Transação atômica
        transaction = db.transaction()
        
        @firestore.transactional
        def update_user_transaction(transaction):
            """Função transacional para atualizar usuário."""
            users_ref = db.collection('users')
            
            # Busca usuário atual
            doc_ref = users_ref.document(current_username)
            snapshot = doc_ref.get(transaction=transaction)
            
            if not snapshot.exists:
                # Fallback: busca por query
                query = users_ref.where('username', '==', current_username).limit(1)
                docs = list(query.stream())
                if not docs:
                    raise UserNotFoundError("Usuário não encontrado.")
                doc_ref = users_ref.document(docs[0].id)
                snapshot = doc_ref.get(transaction=transaction)
            
            if not snapshot.exists:
                raise UserNotFoundError("Usuário não encontrado.")
            
            current_data = snapshot.to_dict()
            
            # Prepara updates
            updates = {
                'name': name,
                'role': role,
                'modules': modules,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            token = None
            
            # LÓGICA CRÍTICA: Mudança de E-mail
            if new_email != current_data.get('email'):
                # Verifica se novo email já existe em outro usuário (na transação)
                email_query = users_ref.where('email', '==', new_email).limit(1)
                email_docs = list(email_query.stream(transaction=transaction))
                for doc in email_docs:
                    if doc.id != snapshot.id:  # Não é o mesmo usuário
                        raise DuplicateUserError("Este novo e-mail já está em uso.")
                
                # Prepara reset de segurança
                token = str(uuid.uuid4())
                updates['email'] = new_email
                updates['username'] = new_email  # Atualiza o login também
                updates['verified'] = False  # Bloqueia acesso
                updates['verification_token'] = token
                
                logger.info(f"Email alterado para {new_email}, gerando novo token")
            
            # Aplica updates na transação
            transaction.update(doc_ref, updates)
            
            return token
        
        # Executa transação
        token = update_user_transaction(transaction)
        
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        if token:
            logger.info(
                "update_user_success_email_changed",
                extra={
                    "current_username": current_username,
                    "new_email": new_email,
                    "duration_ms": duration_ms
                }
            )
            return True, "E-mail alterado! Login atualizado. Revalidação necessária.", token
        else:
            logger.info(
                "update_user_success",
                extra={
                    "current_username": current_username,
                    "duration_ms": duration_ms
                }
            )
            return True, "Dados atualizados com sucesso.", None
        
    except (UserNotFoundError, DuplicateUserError) as e:
        logger.warning(f"update_user_error: {str(e)}")
        return False, str(e), None
    except Exception as e:
        logger.error(
            "update_user_error",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            },
            exc_info=True
        )
        return False, f"Erro ao atualizar usuário: {str(e)}", None


def verify_user_token(token: str) -> Tuple[bool, str]:
    """
    Verifica token de usuário e ativa conta.
    
    Args:
        token: Token de verificação
        
    Returns:
        Tuple[sucesso, mensagem]
    """
    logger.info("verify_user_token_started", extra={"token": token[:10] + "..."})
    
    db = get_db()
    if not db:
        logger.error("verify_user_token_failed: Banco offline")
        return False, "Erro de conexão."
    
    try:
        users_ref = db.collection('users')
        query = users_ref.where('verification_token', '==', token).limit(1)
        docs = list(query.stream())
        
        if not docs:
            logger.warning("verify_user_token_invalid: Token não encontrado")
            return False, "Token inválido."
        
        doc = docs[0]
        doc_ref = users_ref.document(doc.id)
        
        # Atualiza usuário
        doc_ref.update({
            'verified': True,
            'verification_token': firestore.DELETE_FIELD
        })
        
        user_name = doc.get('name', 'Usuário')
        logger.info("verify_user_token_success", extra={"user_id": doc.id})
        
        return True, f"Conta de {user_name} ativada!"
        
    except Exception as e:
        logger.error(
            "verify_user_token_error",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            },
            exc_info=True
        )
        return False, f"Erro ao verificar token: {str(e)}"


def list_all_users() -> List[Dict[str, Any]]:
    """
    Lista todos os usuários do sistema.
    
    Returns:
        Lista de dicionários com dados dos usuários
    """
    logger.debug("list_all_users_started")
    
    db = get_db()
    if not db:
        logger.warning("list_all_users_failed: Banco offline")
        return []
    
    try:
        users = []
        for doc in db.collection('users').stream():
            user_data = doc.to_dict()
            # Remove senha por segurança
            if 'password' in user_data:
                user_data['password'] = '***'
            users.append(user_data)
        
        logger.info(f"list_all_users_success: {len(users)} usuários encontrados")
        return users
        
    except Exception as e:
        logger.error(
            "list_all_users_error",
            extra={
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        return []
