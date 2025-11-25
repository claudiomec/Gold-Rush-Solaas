#!/bin/bash

# Script para fazer commit e push automático para o GitHub
# Uso: ./push_to_github.sh "mensagem do commit"

echo "🚀 Preparando para enviar alterações para o GitHub..."

# Verificar se há mudanças
if [ -z "$(git status --porcelain)" ]; then
    echo "✅ Nenhuma alteração para commitar."
    exit 0
fi

# Mostrar status
echo ""
echo "📋 Alterações detectadas:"
git status -s
echo ""

# Adicionar todas as alterações
echo "➕ Adicionando arquivos..."
git add .

# Mensagem do commit
if [ -z "$1" ]; then
    COMMIT_MSG="feat: Atualização automática - $(date '+%Y-%m-%d %H:%M:%S')"
else
    COMMIT_MSG="$1"
fi

# Fazer commit
echo "💾 Fazendo commit: $COMMIT_MSG"
git commit -m "$COMMIT_MSG"

# Fazer push
echo "📤 Enviando para o GitHub..."
git push origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Sucesso! Alterações enviadas para o GitHub."
    echo "🔗 Repositório: https://github.com/claudiomec/Gold-Rush-Solaas"
else
    echo ""
    echo "❌ Erro ao enviar para o GitHub. Verifique sua conexão e credenciais."
    exit 1
fi

