"""
Módulo de Two Factor Authentication - Autenticação de dois fatores
Responsável por implementar 2FA usando TOTP.
"""
import streamlit as st
import logging
import base64
import io
from typing import Optional, Tuple
from modules.database import get_db
from firebase_admin import firestore

# Configuração de logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Tenta importar bibliotecas de 2FA (opcional)
try:
    import pyotp
    import qrcode
    HAS_2FA_LIBS = True
except ImportError:
    HAS_2FA_LIBS = False
    logger.warning("pyotp ou qrcode não disponíveis. 2FA não funcionará.")


# ============================================================================
# FUNÇÕES DE 2FA
# ============================================================================

def generate_secret_key() -> Optional[str]:
    """
    Gera chave secreta para TOTP.
    
    Returns:
        Chave secreta em base32 ou None se bibliotecas não disponíveis
    """
    if not HAS_2FA_LIBS:
        return None
    
    try:
        return pyotp.random_base32()
    except Exception as e:
        logger.error(f"Erro ao gerar chave secreta: {e}", exc_info=True)
        return None


def generate_qr_code(secret: str, user_email: str, issuer: str = "Gold Rush Analytics") -> Optional[bytes]:
    """
    Gera QR code para configuração de 2FA.
    
    Args:
        secret: Chave secreta
        user_email: Email do usuário
        issuer: Nome do serviço
        
    Returns:
        Bytes da imagem do QR code ou None
    """
    if not HAS_2FA_LIBS:
        return None
    
    try:
        # Cria URI TOTP
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_email,
            issuer_name=issuer
        )
        
        # Gera QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Converte para bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return img_bytes.read()
        
    except Exception as e:
        logger.error(f"Erro ao gerar QR code: {e}", exc_info=True)
        return None


def verify_totp_code(secret: str, code: str) -> bool:
    """
    Verifica código TOTP.
    
    Args:
        secret: Chave secreta
        code: Código de 6 dígitos
        
    Returns:
        True se válido, False caso contrário
    """
    if not HAS_2FA_LIBS:
        return False
    
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)  # Permite 1 período de tolerância
    except Exception as e:
        logger.error(f"Erro ao verificar código TOTP: {e}", exc_info=True)
        return False


def enable_2fa(user_id: str, secret: str) -> Tuple[bool, str]:
    """
    Habilita 2FA para usuário.
    
    Args:
        user_id: ID do usuário
        secret: Chave secreta
        
    Returns:
        Tuple[sucesso, mensagem]
    """
    logger.info(f"enable_2fa_started: {user_id}")
    
    db = get_db()
    if not db:
        logger.error("enable_2fa_failed: Banco offline")
        return False, "Banco Offline."
    
    try:
        users_ref = db.collection('users')
        query = users_ref.where('username', '==', user_id).limit(1)
        docs = list(query.stream())
        
        if not docs:
            return False, "Usuário não encontrado."
        
        doc_ref = docs[0].reference
        doc_ref.update({
            'two_factor_enabled': True,
            'two_factor_secret': secret,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        
        logger.info(f"enable_2fa_success: {user_id}")
        return True, "2FA habilitado com sucesso!"
        
    except Exception as e:
        logger.error(
            "enable_2fa_error",
            extra={
                "user_id": user_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        return False, f"Erro ao habilitar 2FA: {str(e)}"


def disable_2fa(user_id: str) -> Tuple[bool, str]:
    """
    Desabilita 2FA para usuário.
    
    Args:
        user_id: ID do usuário
        
    Returns:
        Tuple[sucesso, mensagem]
    """
    logger.info(f"disable_2fa_started: {user_id}")
    
    db = get_db()
    if not db:
        logger.error("disable_2fa_failed: Banco offline")
        return False, "Banco Offline."
    
    try:
        users_ref = db.collection('users')
        query = users_ref.where('username', '==', user_id).limit(1)
        docs = list(query.stream())
        
        if not docs:
            return False, "Usuário não encontrado."
        
        doc_ref = docs[0].reference
        doc_ref.update({
            'two_factor_enabled': False,
            'two_factor_secret': firestore.DELETE_FIELD,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        
        logger.info(f"disable_2fa_success: {user_id}")
        return True, "2FA desabilitado com sucesso!"
        
    except Exception as e:
        logger.error(
            "disable_2fa_error",
            extra={
                "user_id": user_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        return False, f"Erro ao desabilitar 2FA: {str(e)}"


def is_2fa_enabled(user_id: str) -> bool:
    """
    Verifica se 2FA está habilitado para usuário.
    
    Args:
        user_id: ID do usuário
        
    Returns:
        True se habilitado, False caso contrário
    """
    db = get_db()
    if not db:
        return False
    
    try:
        users_ref = db.collection('users')
        query = users_ref.where('username', '==', user_id).limit(1)
        docs = list(query.stream())
        
        if docs:
            user_data = docs[0].to_dict()
            return user_data.get('two_factor_enabled', False)
        
        return False
        
    except Exception as e:
        logger.error(f"Erro ao verificar 2FA: {e}", exc_info=True)
        return False


def get_2fa_secret(user_id: str) -> Optional[str]:
    """
    Retorna chave secreta de 2FA do usuário.
    
    Args:
        user_id: ID do usuário
        
    Returns:
        Chave secreta ou None
    """
    db = get_db()
    if not db:
        return None
    
    try:
        users_ref = db.collection('users')
        query = users_ref.where('username', '==', user_id).limit(1)
        docs = list(query.stream())
        
        if docs:
            user_data = docs[0].to_dict()
            return user_data.get('two_factor_secret')
        
        return None
        
    except Exception as e:
        logger.error(f"Erro ao buscar chave 2FA: {e}", exc_info=True)
        return None

