# 📖 Guia Detalhado de Atualização Local

## 🔍 Diagnóstico de Problemas

### Problema 1: "Não é um repositório Git"
**Sintoma:** `fatal: not a git repository`

**Solução:**
```bash
cd /Users/claudioeduardoferreira/Downloads/Gold-Rush-Solaas
git init
git remote add origin https://github.com/claudiomec/Gold-Rush-Solaas.git
git fetch origin
git checkout -b main origin/main
```

### Problema 2: "Conflitos de Merge"
**Sintoma:** `CONFLICT (content): Merge conflict in arquivo.py`

**Solução Manual:**
1. Abra o arquivo com conflito
2. Procure por marcadores: `<<<<<<<`, `=======`, `>>>>>>>`
3. Escolha qual versão manter ou combine ambas
4. Remova os marcadores de conflito
5. Execute:
```bash
git add .
git commit -m "Resolve conflitos"
```

**Solução Automática (manter versão do GitHub):**
```bash
git checkout --theirs .
git add .
git commit -m "Aceita versão do GitHub"
```

**Solução Automática (manter versão local):**
```bash
git checkout --ours .
git add .
git commit -m "Mantém versão local"
```

### Problema 3: "Mudanças locais não commitadas"
**Sintoma:** `error: Your local changes to the following files would be overwritten`

**Opção A - Salvar mudanças:**
```bash
git stash push -m "Minhas mudanças locais"
git pull origin main
git stash pop  # Para recuperar depois
```

**Opção B - Descartar mudanças:**
```bash
git reset --hard HEAD
git pull origin main
```

**Opção C - Fazer commit primeiro:**
```bash
git add .
git commit -m "Minhas mudanças locais"
git pull origin main
```

### Problema 4: "Branch divergente"
**Sintoma:** `fatal: refusing to merge unrelated histories`

**Solução:**
```bash
git pull origin main --allow-unrelated-histories
```

### Problema 5: "Permissão negada"
**Sintoma:** `Permission denied (publickey)`

**Solução:**
Use HTTPS em vez de SSH:
```bash
git remote set-url origin https://github.com/claudiomec/Gold-Rush-Solaas.git
git pull origin main
```

## 📝 Passo a Passo Completo

### Método 1: Usando o Script Automático (Recomendado)

1. **Baixe o script:**
```bash
cd /Users/claudioeduardoferreira/Downloads/Gold-Rush-Solaas
curl -O https://raw.githubusercontent.com/claudiomec/Gold-Rush-Solaas/main/atualizar_local.sh
chmod +x atualizar_local.sh
```

2. **Execute o script:**
```bash
./atualizar_local.sh
```

### Método 2: Manual (Passo a Passo)

#### Passo 1: Navegue até o diretório
```bash
cd /Users/claudioeduardoferreira/Downloads/Gold-Rush-Solaas
```

#### Passo 2: Verifique o status
```bash
git status
```

#### Passo 3: Se houver mudanças locais, decida:

**A) Salvar em stash (temporário):**
```bash
git stash push -m "Backup antes da atualização"
```

**B) Fazer commit:**
```bash
git add .
git commit -m "Minhas mudanças locais"
```

**C) Descartar (CUIDADO - perde mudanças):**
```bash
git reset --hard HEAD
```

#### Passo 4: Atualize do GitHub
```bash
git fetch origin
git pull origin main
```

#### Passo 5: Se houver conflitos, resolva:
```bash
# Veja os arquivos com conflito
git status

# Edite os arquivos manualmente ou use:
git checkout --theirs .  # Aceita versão do GitHub
# OU
git checkout --ours .    # Mantém versão local

git add .
git commit -m "Resolve conflitos"
```

#### Passo 6: Limpe o cache
```bash
rm -rf ~/.streamlit/cache
```

#### Passo 7: Atualize dependências
```bash
pip install -r requirements.txt --upgrade
```

#### Passo 8: Teste
```bash
streamlit run app.py
```

## 🔧 Comandos Úteis

### Ver histórico de commits
```bash
git log --oneline -10
```

### Ver diferenças locais
```bash
git diff
```

### Ver branches remotas
```bash
git branch -a
```

### Resetar para versão do GitHub (PERIGOSO)
```bash
git fetch origin
git reset --hard origin/main
```

### Ver mudanças não commitadas
```bash
git status
git diff
```

### Recuperar mudanças do stash
```bash
git stash list
git stash pop
```

## 🆘 Ainda com Problemas?

### Opção Nuclear: Clonar Novamente

Se nada funcionar, você pode clonar o repositório em um novo diretório:

```bash
cd /Users/claudioeduardoferreira/Downloads
mv Gold-Rush-Solaas Gold-Rush-Solaas-backup
git clone https://github.com/claudiomec/Gold-Rush-Solaas.git
cd Gold-Rush-Solaas
```

Depois copie seus arquivos de configuração do backup:
```bash
cp ../Gold-Rush-Solaas-backup/.streamlit/secrets.toml .streamlit/
```

## 📞 Informações para Diagnóstico

Se ainda não funcionar, execute estes comandos e compartilhe o resultado:

```bash
cd /Users/claudioeduardoferreira/Downloads/Gold-Rush-Solaas
git status
git remote -v
git branch -a
git log --oneline -5
```

Isso ajudará a identificar o problema específico.
