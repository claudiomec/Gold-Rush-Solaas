#!/bin/bash

# Script executado após a criação do container
echo "🚀 Configurando ambiente Gold Rush Analytics..."

# Atualizar pip
pip install --upgrade pip

# Instalar dependências
echo "📦 Instalando dependências..."
pip install -r requirements.txt

# Configurar Streamlit
echo "⚙️ Configurando Streamlit..."
mkdir -p ~/.streamlit

# Criar arquivo de configuração do Streamlit
cat > ~/.streamlit/config.toml << EOF
[server]
port = 8501
address = "0.0.0.0"
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false
EOF

echo "✅ Ambiente configurado com sucesso!"
echo ""
echo "Para iniciar a aplicação, execute:"
echo "  streamlit run app.py"
echo ""

