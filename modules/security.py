"""
Módulo de segurança - Hash de senhas e funções de segurança
"""
import bcrypt

def hash_password(password: str) -> str:
    """
    Gera hash seguro da senha usando bcrypt.
    
    Args:
        password: Senha em texto plano
        
    Returns:
        Hash da senha em formato string
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def check_password(password: str, hashed: str) -> bool:
    """
    Verifica se a senha corresponde ao hash.
    
    Args:
        password: Senha em texto plano
        hashed: Hash armazenado
        
    Returns:
        True se a senha corresponde, False caso contrário
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        print(f"Erro ao verificar senha: {e}")
        return False

def is_password_hashed(password_field: str) -> bool:
    """
    Verifica se uma string parece ser um hash bcrypt.
    Bcrypt hashes começam com $2b$ ou $2a$ e têm 60 caracteres.
    
    Args:
        password_field: Campo que pode ser senha ou hash
        
    Returns:
        True se parece ser um hash, False caso contrário
    """
    if not password_field:
        return False
    return password_field.startswith('$2') and len(password_field) == 60

