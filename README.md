# 🏭 Gold Rush Analytics

Sistema de monitoramento e análise de custos industriais com interface moderna e dinâmica.

## 🚀 Como Usar

### Opção 1: GitHub Codespaces (Recomendado - Editar Diretamente no GitHub)

1. **Acesse o repositório no GitHub:**
   - Vá para: https://github.com/claudiomec/Gold-Rush-Solaas

2. **Crie um Codespace:**
   - Clique no botão verde **"Code"**
   - Selecione a aba **"Codespaces"**
   - Clique em **"Create codespace on main"**
   - Aguarde o ambiente ser criado (2-3 minutos)

3. **Execute a aplicação:**
   ```bash
   streamlit run app.py
   ```

4. **Acesse a aplicação:**
   - O Streamlit abrirá automaticamente em uma nova aba
   - Ou acesse a URL que aparecerá no terminal

### Opção 2: Edição Local

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/claudiomec/Gold-Rush-Solaas.git
   cd Gold-Rush-Solaas
   ```

2. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Execute a aplicação:**
   ```bash
   streamlit run app.py
   ```

## 📋 Requisitos

- Python 3.11+
- Dependências listadas em `requirements.txt`

## 🎨 Funcionalidades

- 📊 **Monitor de Custo Industrial**: Acompanhamento em tempo real de preços
- 💰 **Calculadora Financeira**: Análise de impacto financeiro de compras
- 📈 **Gráficos Interativos**: Visualizações dinâmicas com Plotly
- 👥 **Gestão de Usuários**: Sistema de acesso e permissões
- 📄 **Relatórios PDF**: Geração automática de laudos

## 🛠️ Tecnologias

- **Streamlit**: Framework web
- **Plotly**: Gráficos interativos
- **Firebase**: Banco de dados
- **Pandas**: Análise de dados
- **YFinance**: Dados de mercado

## 📁 Estrutura do Projeto

```
Gold-Rush-Solaas/
├── app.py                 # Aplicação principal
├── modules/               # Módulos do sistema
│   ├── auth.py           # Autenticação
│   ├── database.py       # Banco de dados
│   ├── data_engine.py    # Processamento de dados
│   ├── ui_components.py  # Componentes de UI
│   └── ...
├── scripts/              # Scripts auxiliares
└── requirements.txt      # Dependências
```

## 🔧 Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` (não commitado) com:

```
FIREBASE_CREDENTIALS=path/to/firebase-key.json
```

### Firebase

Configure suas credenciais do Firebase no módulo `database.py`.

## 📝 Licença

Este projeto é privado e proprietário.

## 👤 Autor

Claudio Eduardo Ferreira

---

**💡 Dica**: Use GitHub Codespaces para editar diretamente no navegador sem precisar configurar nada localmente!

