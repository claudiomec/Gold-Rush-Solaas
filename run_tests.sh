#!/bin/bash

# Script para executar testes unitários

echo "🧪 Executando testes unitários do Gold Rush SAAS"
echo "================================================"
echo ""

# Verifica se pytest está instalado
if ! command -v pytest &> /dev/null; then
    echo "⚠️  pytest não encontrado. Instalando..."
    pip install pytest pytest-cov
fi

# Executa testes
echo "📊 Executando testes..."
python -m pytest tests/ -v --tb=short

# Verifica resultado
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Todos os testes passaram!"
else
    echo ""
    echo "❌ Alguns testes falharam. Verifique os erros acima."
    exit 1
fi

