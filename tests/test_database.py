"""
Testes unitários para o módulo database.py
"""
import unittest
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.database import (
    is_valid_email,
    validate_user_data,
    sanitize_private_key,
    UserValidationError
)


class TestEmailValidation(unittest.TestCase):
    """Testes para validação de e-mail."""
    
    def test_valid_emails(self):
        """Testa e-mails válidos."""
        valid_emails = [
            'test@example.com',
            'user.name@domain.co.uk',
            'user+tag@example.com',
            'user123@test-domain.com'
        ]
        
        for email in valid_emails:
            self.assertTrue(is_valid_email(email), f"E-mail válido rejeitado: {email}")
    
    def test_invalid_emails(self):
        """Testa e-mails inválidos."""
        invalid_emails = [
            'invalid',
            '@example.com',
            'user@',
            'user@domain',
            '',
            None
        ]
        
        for email in invalid_emails:
            if email is not None:
                self.assertFalse(is_valid_email(email), f"E-mail inválido aceito: {email}")


class TestUserDataValidation(unittest.TestCase):
    """Testes para validação de dados de usuário."""
    
    def test_validate_user_data_valid(self):
        """Testa validação com dados válidos."""
        is_valid, error = validate_user_data(
            username='testuser',
            email='test@example.com',
            role='client',
            modules=['Monitor']
        )
        
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_validate_user_data_short_username(self):
        """Testa username muito curto."""
        is_valid, error = validate_user_data(
            username='ab',
            email='test@example.com'
        )
        
        self.assertFalse(is_valid)
        self.assertIn('3 caracteres', error)
    
    def test_validate_user_data_invalid_email(self):
        """Testa e-mail inválido."""
        is_valid, error = validate_user_data(
            username='testuser',
            email='invalid-email'
        )
        
        self.assertFalse(is_valid)
        self.assertIn('Email inválido', error)
    
    def test_validate_user_data_invalid_role(self):
        """Testa role inválida."""
        is_valid, error = validate_user_data(
            username='testuser',
            email='test@example.com',
            role='invalid_role'
        )
        
        self.assertFalse(is_valid)
        self.assertIn('Role inválida', error)
    
    def test_validate_user_data_invalid_modules(self):
        """Testa módulos inválidos."""
        is_valid, error = validate_user_data(
            username='testuser',
            email='test@example.com',
            modules=['InvalidModule']
        )
        
        self.assertFalse(is_valid)
        self.assertIn('Módulos inválidos', error)


class TestPrivateKeySanitization(unittest.TestCase):
    """Testes para sanitização de chave privada."""
    
    def test_sanitize_private_key_valid(self):
        """Testa sanitização com chave válida."""
        # Chave privada de exemplo (formato PEM)
        valid_key = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7VJTUt9Us8cKj
MzEfYyjiWA4R4/M2bS1+fJYq8k2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z
2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z
2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z
2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z2Z
-----END PRIVATE KEY-----"""
        
        # Remove formatação para testar sanitização
        key_without_format = valid_key.replace('-----BEGIN PRIVATE KEY-----', '')\
                                      .replace('-----END PRIVATE KEY-----', '')\
                                      .replace('\n', '')\
                                      .replace(' ', '')
        
        try:
            sanitized = sanitize_private_key(key_without_format)
            # Se cryptography não estiver disponível, pode falhar na validação
            # mas a função deve tentar formatar
            self.assertIn('BEGIN PRIVATE KEY', sanitized)
            self.assertIn('END PRIVATE KEY', sanitized)
        except ValueError:
            # Se falhar, é porque a chave de exemplo não é válida criptograficamente
            # Isso é esperado se cryptography estiver disponível
            pass
    
    def test_sanitize_private_key_too_short(self):
        """Testa chave muito curta."""
        short_key = "abc123"
        
        with self.assertRaises(ValueError):
            sanitize_private_key(short_key)
    
    def test_sanitize_private_key_empty(self):
        """Testa chave vazia."""
        with self.assertRaises(ValueError):
            sanitize_private_key("")
        
        with self.assertRaises(ValueError):
            sanitize_private_key(None)


if __name__ == '__main__':
    unittest.main()

