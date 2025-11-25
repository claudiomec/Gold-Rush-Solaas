#!/bin/bash

# Script para atualizar o código local do Gold Rush
# Uso: ./atualizar_local.sh

echo "🔄 Iniciando atualização do Gold Rush..."
echo ""

# Verifica se está no diretório correto
if [ ! -f "app.py" ]; then
    echo "❌ Erro: app.py não encontrado!"
    echo "   Certifique-se de estar no diretório do projeto Gold-Rush-Solaas"
    exit 1
fi

# 1. Verifica status do git
echo "📊 Verificando status do Git..."
git status

echo ""
read -p "Deseja continuar? (s/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "❌ Atualização cancelada."
    exit 1
fi

# 2. Faz backup das mudanças locais (se houver)
echo ""
echo "💾 Fazendo backup das mudanças locais..."
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "   ⚠️  Há mudanças locais não commitadas"
    BACKUP_BRANCH="backup-local-$(date +%Y%m%d-%H%M%S)"
    git stash push -m "Backup antes da atualização - $BACKUP_BRANCH"
    echo "   ✅ Mudanças salvas em stash: $BACKUP_BRANCH"
fi

# 3. Atualiza do GitHub
echo ""
echo "⬇️  Baixando atualizações do GitHub..."
git fetch origin

# 4. Tenta fazer merge
echo ""
echo "🔀 Mesclando mudanças..."
if git pull origin main; then
    echo "   ✅ Atualização concluída com sucesso!"
else
    echo "   ⚠️  Conflitos detectados durante o merge"
    echo ""
    echo "   Para resolver manualmente:"
    echo "   1. Edite os arquivos com conflitos (procure por <<<<<<<)"
    echo "   2. Resolva os conflitos"
    echo "   3. Execute: git add ."
    echo "   4. Execute: git commit -m 'Resolve conflitos'"
    echo ""
    echo "   Ou para cancelar e manter sua versão local:"
    echo "   git merge --abort"
    exit 1
fi

# 5. Limpa cache do Streamlit
echo ""
echo "🧹 Limpando cache do Streamlit..."
rm -rf ~/.streamlit/cache 2>/dev/null
echo "   ✅ Cache limpo"

# 6. Verifica dependências
echo ""
echo "📦 Verificando dependências..."
if [ -f "requirements.txt" ]; then
    echo "   Instalando/atualizando pacotes..."
    pip install -r requirements.txt --quiet --upgrade
    echo "   ✅ Dependências atualizadas"
fi

echo ""
echo "✅ Atualização concluída!"
echo ""
echo "Para iniciar o Streamlit:"
echo "   streamlit run app.py"
echo ""
echo "Se precisar recuperar suas mudanças locais:"
echo "   git stash list"
echo "   git stash pop"
