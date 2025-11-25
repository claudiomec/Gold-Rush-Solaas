# Como Atualizar o Código Localmente

## ✅ Código já atualizado no GitHub!

Todas as correções foram commitadas e enviadas para o repositório GitHub.

## Passos para Atualizar Localmente

### 1. Navegue até a pasta do projeto
```bash
cd /Users/claudioeduardoferreira/Downloads/Gold-Rush-Solaas
```

### 2. Verifique se há mudanças locais não commitadas
```bash
git status
```

### 3. Se houver mudanças locais que deseja manter:
```bash
# Faça commit das suas mudanças primeiro
git add .
git commit -m "Minhas mudanças locais"
```

### 4. Atualize do GitHub
```bash
# Puxe as últimas mudanças
git pull origin main
```

### 5. Se houver conflitos:
O Git pode pedir para resolver conflitos. Nesse caso:
- Resolva os conflitos manualmente nos arquivos indicados
- Ou use: `git merge --abort` para cancelar e depois `git pull --rebase origin main`

### 5. Limpe o cache do Streamlit (IMPORTANTE!)
```bash
rm -rf ~/.streamlit/cache
```

### 6. Reinicie o Streamlit
```bash
streamlit run app.py
```

## O que foi atualizado?

✅ **Segurança**: Uso de bcrypt para hash de senhas (mais seguro)
✅ **Tratamento de Erros**: get_db() nunca levanta exceções, sempre retorna None
✅ **Cálculos Temporais**: Variação calculada por tempo real (7 dias) em vez de linhas fixas
✅ **Encoding PDF**: Suporte correto para caracteres especiais (acentos)
✅ **Duplicação**: Verificação robusta de usuários duplicados

## Arquivos Modificados

- `modules/database.py` - Tratamento de erros melhorado
- `modules/auth.py` - Suporte a bcrypt e tratamento de erros
- `app.py` - Cálculo de variação corrigido
- `modules/report_generator.py` - Encoding PDF corrigido
- `modules/data_engine.py` - Rolling window baseado em tempo
- `scripts/daily_etl.py` - Cálculos temporais corrigidos

## Se encontrar problemas

Consulte o arquivo `SOLUCAO_ERRO_CONEXAO.md` para guias de solução de problemas comuns.
