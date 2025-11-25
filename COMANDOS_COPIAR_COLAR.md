# 📋 Comandos para Copiar e Colar

## 🚀 Atualização Rápida (Copie e Cole Tudo)

Abra o Terminal e cole estes comandos um por um:

```bash
# 1. Ir para o diretório do projeto
cd /Users/claudioeduardoferreira/Downloads/Gold-Rush-Solaas

# 2. Verificar status
git status

# 3. Salvar mudanças locais (se houver)
git stash push -m "Backup antes da atualização"

# 4. Baixar atualizações
git fetch origin

# 5. Atualizar código
git pull origin main

# 6. Limpar cache do Streamlit
rm -rf ~/.streamlit/cache

# 7. Atualizar dependências
pip install -r requirements.txt --upgrade

# 8. Testar
streamlit run app.py
```

## 🔧 Se Der Erro de Conflito

Se aparecer "CONFLICT", execute:

```bash
# Aceitar versão do GitHub (recomendado)
git checkout --theirs .
git add .
git commit -m "Atualização do GitHub"
```

## 🔄 Se Não For um Repositório Git

Se aparecer "not a git repository", execute:

```bash
cd /Users/claudioeduardoferreira/Downloads/Gold-Rush-Solaas
git init
git remote add origin https://github.com/claudiomec/Gold-Rush-Solaas.git
git fetch origin
git checkout -b main origin/main
```

## 📦 Se Precisar Clonar do Zero

Se nada funcionar, clone novamente:

```bash
cd /Users/claudioeduardoferreira/Downloads
mv Gold-Rush-Solaas Gold-Rush-Solaas-backup
git clone https://github.com/claudiomec/Gold-Rush-Solaas.git
cd Gold-Rush-Solaas
cp ../Gold-Rush-Solaas-backup/.streamlit/secrets.toml .streamlit/ 2>/dev/null || echo "Arquivo secrets.toml não encontrado no backup"
```
