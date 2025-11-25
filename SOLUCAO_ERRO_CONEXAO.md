# Solução para Erro de Conexão com Firebase

## Problema
Erro ao tentar conectar com Firebase durante autenticação:
```
DatabaseConnectionError: Chave privada inválida
```

## Soluções

### 1. Limpar Cache do Streamlit
O cache do Streamlit pode estar armazenando uma conexão inválida. Execute:

```bash
# No terminal, na raiz do projeto
rm -rf ~/.streamlit/cache
```

Ou no Python/Streamlit, adicione temporariamente no início do `app.py`:

```python
from modules.database import clear_db_cache
clear_db_cache()
```

### 2. Verificar Arquivo de Secrets
Certifique-se de que o arquivo `.streamlit/secrets.toml` existe e está no formato correto:

```toml
[firebase]
type = "service_account"
project_id = "seu-project-id"
private_key_id = "sua-key-id"
client_email = "seu-email@project.iam.gserviceaccount.com"
# ... outros campos ...

private_key = """-----BEGIN PRIVATE KEY-----
SUA_CHAVE_AQUI
-----END PRIVATE KEY-----"""
```

**Importante**: A `private_key` deve estar entre aspas triplas (`"""`) e manter as quebras de linha.

### 3. Reiniciar o Streamlit
Após fazer alterações, reinicie completamente o servidor Streamlit:

```bash
# Pare o servidor (Ctrl+C) e inicie novamente
streamlit run app.py
```

### 4. Verificar Credenciais do Firebase
- Acesse o [Console do Firebase](https://console.firebase.google.com/)
- Vá em Configurações do Projeto > Contas de Serviço
- Gere uma nova chave privada se necessário
- Certifique-se de que a chave está completa e válida

### 5. Usar Modo de Fallback (Admin via Secrets)
Se o Firebase não estiver disponível, você pode usar o login de admin via `secrets.toml`:

```toml
[users]
    [users.admin]
    name = "Admin"
    password = "senha_admin"
    role = "admin"
```

O sistema tentará primeiro o Firebase e, se falhar, usará os usuários do `secrets.toml`.

### 6. Verificar Logs
Os erros agora são impressos no console com mensagens claras. Verifique o terminal onde o Streamlit está rodando para ver mensagens como:
- `⚠️ Aviso: Credenciais do Firebase não encontradas`
- `❌ Erro de validação das credenciais Firebase`
- `❌ Erro ao processar chave privada`

Essas mensagens indicam exatamente qual é o problema.

## Código Atualizado

O código foi atualizado para:
- ✅ Nunca levantar exceções (sempre retorna `None` em caso de erro)
- ✅ Mensagens de erro claras e informativas
- ✅ Tratamento robusto de todos os tipos de erro
- ✅ Fallback automático para usuários do `secrets.toml`

Se o problema persistir, verifique os logs no console para identificar a causa específica.
