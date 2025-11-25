import streamlit as st
import plotly.graph_objects as go
import streamlit_antd_components as sac

def load_custom_css():
    """Carrega o tema visual Gold Rush (Dark Mode Moderno e Dinâmico)."""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        
        /* Variáveis CSS */
        :root {
            --gold-primary: #FFD700;
            --gold-secondary: #FFA500;
            --bg-primary: #0A0E1A;
            --bg-secondary: #141B2D;
            --bg-card: #1A2332;
            --text-primary: #FFFFFF;
            --text-secondary: #B8C5D6;
            --accent-green: #00E676;
            --accent-red: #FF5252;
            --accent-blue: #448AFF;
        }
        
        /* Fundo Geral com Gradiente Animado */
        .stApp { 
            background: linear-gradient(135deg, #0A0E1A 0%, #141B2D 50%, #0F1624 100%);
            background-attachment: fixed;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        /* Animação de fundo sutil */
        @keyframes gradientShift {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }
        
        /* Ajustes de Espaçamento */
        .block-container { 
            padding-top: 2rem; 
            padding-bottom: 2rem; 
            max-width: 1400px;
        }
        
        /* Sidebar Moderna */
        section[data-testid="stSidebar"] { 
            background: linear-gradient(180deg, #141B2D 0%, #0F1624 100%);
            border-right: 1px solid rgba(255, 215, 0, 0.1);
            box-shadow: 2px 0 20px rgba(0, 0, 0, 0.3);
        }
        
        /* Títulos e Textos Modernos */
        h1 { 
            color: var(--gold-primary) !important; 
            font-family: 'Inter', sans-serif !important;
            font-weight: 700 !important;
            font-size: 2.5rem !important;
            text-shadow: 0 0 20px rgba(255, 215, 0, 0.3);
            letter-spacing: -0.5px;
            margin-bottom: 1rem !important;
        }
        h2 { 
            color: var(--gold-primary) !important; 
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            font-size: 1.8rem !important;
        }
        h3 { 
            color: var(--gold-secondary) !important; 
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
        }
        p, label, span, .stMarkdown { 
            color: var(--text-secondary) !important; 
            font-family: 'Inter', sans-serif !important;
        }
        
        /* Cards de Métricas (KPIs) Modernos */
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, var(--bg-card) 0%, #1F2A3E 100%);
            border: 1px solid rgba(255, 215, 0, 0.15);
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 
                        0 0 0 1px rgba(255, 215, 0, 0.05) inset;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }
        
        div[data-testid="stMetric"]::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--gold-primary), var(--gold-secondary));
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        
        div[data-testid="stMetric"]:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5), 
                        0 0 20px rgba(255, 215, 0, 0.1);
            border-color: rgba(255, 215, 0, 0.3);
        }
        
        div[data-testid="stMetric"]:hover::before {
            opacity: 1;
        }
        
        div[data-testid="stMetricLabel"] { 
            color: var(--text-secondary) !important; 
            font-weight: 500 !important;
            font-size: 0.9rem !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        div[data-testid="stMetricValue"] { 
            color: var(--text-primary) !important; 
            font-weight: 700 !important;
            font-size: 1.8rem !important;
        }
        div[data-testid="stMetricDelta"] {
            font-weight: 600 !important;
        }
        
        /* Imagem de Login */
        div[data-testid="stImage"] { 
            display: flex; 
            justify-content: center;
            animation: float 3s ease-in-out infinite;
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }
        
        /* Cards Financeiros Customizados Modernos */
        .savings-card { 
            background: linear-gradient(135deg, rgba(0, 230, 118, 0.1) 0%, rgba(0, 200, 83, 0.05) 100%); 
            border: 1px solid rgba(0, 230, 118, 0.3);
            border-left: 4px solid var(--accent-green);
            padding: 24px; 
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0, 230, 118, 0.2),
                        0 0 0 1px rgba(0, 230, 118, 0.1) inset;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .savings-card::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(0, 230, 118, 0.1) 0%, transparent 70%);
            animation: pulse 4s ease-in-out infinite;
        }
        
        .loss-card { 
            background: linear-gradient(135deg, rgba(255, 82, 82, 0.1) 0%, rgba(244, 67, 54, 0.05) 100%); 
            border: 1px solid rgba(255, 82, 82, 0.3);
            border-left: 4px solid var(--accent-red);
            padding: 24px; 
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(255, 82, 82, 0.2),
                        0 0 0 1px rgba(255, 82, 82, 0.1) inset;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .loss-card::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255, 82, 82, 0.1) 0%, transparent 70%);
            animation: pulse 4s ease-in-out infinite;
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 0.5; }
            50% { transform: scale(1.1); opacity: 0.8; }
        }
        
        /* Botões Modernos */
        .stButton > button {
            background: linear-gradient(135deg, var(--gold-primary) 0%, var(--gold-secondary) 100%);
            color: #000 !important;
            font-weight: 600 !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 0.6rem 1.5rem !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3);
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(255, 215, 0, 0.4);
            background: linear-gradient(135deg, #FFE135 0%, #FFB84D 100%);
        }
        
        /* Inputs Modernos */
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div > select {
            background-color: var(--bg-card) !important;
            border: 1px solid rgba(255, 215, 0, 0.2) !important;
            border-radius: 10px !important;
            color: var(--text-primary) !important;
            padding: 0.6rem 1rem !important;
            transition: all 0.3s ease;
        }
        
        .stTextInput > div > div > input:focus,
        .stNumberInput > div > div > input:focus {
            border-color: var(--gold-primary) !important;
            box-shadow: 0 0 0 3px rgba(255, 215, 0, 0.1) !important;
        }
        
        /* Sliders Modernos */
        .stSlider > div > div {
            background: var(--bg-card) !important;
        }
        
        /* Tabs Modernas */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        
        .stTabs [data-baseweb="tab"] {
            background: var(--bg-card) !important;
            border-radius: 10px 10px 0 0 !important;
            border: 1px solid rgba(255, 215, 0, 0.1) !important;
            color: var(--text-secondary) !important;
            transition: all 0.3s ease;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, var(--bg-card) 0%, #1F2A3E 100%) !important;
            color: var(--gold-primary) !important;
            border-color: var(--gold-primary) !important;
            box-shadow: 0 4px 15px rgba(255, 215, 0, 0.2);
        }
        
        /* Formulários */
        .stForm {
            background: var(--bg-card);
            border: 1px solid rgba(255, 215, 0, 0.1);
            border-radius: 16px;
            padding: 2rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        /* Dataframes */
        .stDataFrame {
            border-radius: 12px;
            overflow: hidden;
        }
        
        /* Scrollbar Customizada */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--bg-primary);
        }
        
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(180deg, var(--gold-primary), var(--gold-secondary));
            border-radius: 5px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(180deg, #FFE135, #FFB84D);
        }
        
        /* Efeito de Loading */
        .stSpinner > div {
            border-color: var(--gold-primary) transparent transparent transparent !important;
        }
        
        /* Cards de Alerta */
        .element-container {
            animation: fadeIn 0.5s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        </style>
    """, unsafe_allow_html=True)

def render_sidebar_menu(role, current_modules):
    """Renderiza o menu lateral moderno (Ant Design)."""
    
    # Ícones: https://icons.getbootstrap.com/
    
    if role == "admin":
        # Menu Completo de Admin
        # CORREÇÃO: Removido format_func='title' que estava escondendo os textos
        selected = sac.menu([
            sac.MenuItem('Monitor', icon='graph-up-arrow'),
            sac.MenuItem('Calculadora', icon='calculator'),
            sac.MenuItem('Backtest Lab', icon='flask'),
            sac.MenuItem('Gestão de Dados', icon='database', children=[
                sac.MenuItem('Exportar Excel', icon='file-earmark-excel'),
            ]),
            sac.MenuItem('Usuários', icon='people'),
            sac.MenuItem(type='divider'),
            sac.MenuItem('Logout', icon='box-arrow-right'),
        ], index=0, size='middle', color='yellow', open_all=True)
        
        # Mapeamento de nomes para compatibilidade com o app.py
        if selected == "Exportar Excel": return "Dados (XLSX)"
        if selected == "Calculadora": return "Calculadora Financeira"
        if selected == "Backtest Lab": return "Backtest"
        if selected == "Logout": return "LOGOUT_ACTION"
        return selected

    else:
        # Menu Dinâmico do Cliente (baseado no que contratou)
        menu_items = []
        
        if "Monitor" in current_modules:
            menu_items.append(sac.MenuItem('Monitor', icon='graph-up-arrow'))
        
        if "Calculadora Financeira" in current_modules:
            menu_items.append(sac.MenuItem('Calculadora', icon='calculator'))
            
        menu_items.append(sac.MenuItem(type='divider'))
        menu_items.append(sac.MenuItem('Logout', icon='box-arrow-right'))
        
        selected = sac.menu(menu_items, index=0, size='middle', color='yellow')
        
        if selected == "Calculadora": return "Calculadora Financeira"
        if selected == "Logout": return "LOGOUT_ACTION"
        return selected

def render_price_chart(df):
    """Renderiza gráfico interativo moderno com Plotly."""
    
    # Cria o objeto de figura interativa
    fig = go.Figure()

    # Área de fundo para o preço spot (gradiente)
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['PP_Price'],
        mode='lines',
        name='Spot Diário',
        line=dict(color='rgba(150, 150, 150, 0.3)', width=2),
        fill='tozeroy',
        fillcolor='rgba(150, 150, 150, 0.1)',
        hovertemplate='<b>Spot Diário</b><br>Data: %{x}<br>Preço: R$ %{y:.2f}<extra></extra>'
    ))

    # Linha do Preço Spot (mais visível)
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['PP_Price'],
        mode='lines',
        name='Spot Diário',
        line=dict(color='#9E9E9E', width=2),
        opacity=0.7,
        hovertemplate='<b>Spot Diário</b><br>Data: %{x}<br>Preço: R$ %{y:.2f}<extra></extra>'
    ))

    # Linha da Tendência (Dourada com gradiente e brilho)
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['Trend'],
        mode='lines',
        name='Tendência Gold Rush',
        line=dict(
            color='#FFD700',
            width=4,
            shape='spline',
            smoothing=1.3
        ),
        hovertemplate='<b>Tendência Gold Rush</b><br>Data: %{x}<br>Preço: R$ %{y:.2f}<extra></extra>'
    ))

    # Adiciona área de gradiente sob a linha de tendência
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['Trend'],
        mode='lines',
        name='Área de Tendência',
        line=dict(width=0),
        fill='tozeroy',
        fillcolor='rgba(255, 215, 0, 0.15)',
        showlegend=False,
        hoverinfo='skip'
    ))

    # Marcador no último ponto
    last_idx = df.index[-1]
    last_value = df['Trend'].iloc[-1]
    fig.add_trace(go.Scatter(
        x=[last_idx],
        y=[last_value],
        mode='markers',
        name='Valor Atual',
        marker=dict(
            size=12,
            color='#FFD700',
            line=dict(width=2, color='#FFFFFF'),
            symbol='diamond'
        ),
        hovertemplate='<b>Valor Atual</b><br>Data: %{x}<br>Preço: R$ %{y:.2f}<extra></extra>'
    ))

    # Layout Moderno e Profissional
    fig.update_layout(
        title=dict(
            text="<b>Evolução de Preços</b>",
            font=dict(size=20, color='#FFD700', family='Inter'),
            x=0.5,
            xanchor='center'
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#B8C5D6', family='Inter', size=12),
        margin=dict(l=50, r=30, t=50, b=50),
        height=450,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(26, 35, 50, 0.8)",
            bordercolor="rgba(255, 215, 0, 0.2)",
            borderwidth=1,
            font=dict(size=11),
            itemclick="toggleothers",
            itemdoubleclick="toggle"
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="rgba(26, 35, 50, 0.95)",
            bordercolor="#FFD700",
            font_size=12,
            font_family="Inter"
        ),
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(255, 255, 255, 0.05)',
            showline=True,
            linewidth=1,
            linecolor='rgba(255, 215, 0, 0.2)',
            zeroline=False
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(255, 255, 255, 0.05)',
            showline=True,
            linewidth=1,
            linecolor='rgba(255, 215, 0, 0.2)',
            zeroline=False,
            tickprefix="R$ ",
            tickformat=".2f"
        )
    )
    
    # Configuração do gráfico (sem barra de ferramentas padrão, mas mantém interatividade)
    config = {
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['pan2d', 'lasso2d'],
        'toImageButtonOptions': {
            'format': 'png',
            'filename': 'gold_rush_chart',
            'height': 600,
            'width': 1200,
            'scale': 2
        }
    }

    st.plotly_chart(fig, use_container_width=True, config=config)

def render_insight_card(variation_pct):
    """Renderiza o alerta moderno usando componentes SAC com animações."""
    if variation_pct > 0.5:
        sac.alert(
            label='📈 TENDÊNCIA DE ALTA', 
            description='Pressão de custos detectada. Recomendamos antecipar compras para evitar impactos no orçamento.',
            size='lg', 
            radius=True, 
            icon=True, 
            color='error', 
            banner=False,
            closable=False
        )
    elif variation_pct < -0.5:
        sac.alert(
            label='💎 JANELA DE OPORTUNIDADE', 
            description='Tendência de queda identificada. Considere compras fracionadas ou aguarde melhor momento.',
            size='lg', 
            radius=True, 
            icon=True, 
            color='success', 
            banner=False,
            closable=False
        )
    else:
        sac.alert(
            label='⚖️ MERCADO ESTÁVEL', 
            description='Sem grandes oscilações no curto prazo. Mantenha sua programação de compras normalmente.',
            size='lg', 
            radius=True, 
            icon=True, 
            color='warning', 
            banner=False,
            closable=False
        )

def render_modern_card(title, value, subtitle="", icon="", color="gold"):
    """Renderiza um card moderno e animado."""
    color_map = {
        "gold": {"bg": "rgba(255, 215, 0, 0.1)", "border": "rgba(255, 215, 0, 0.3)", "text": "#FFD700"},
        "green": {"bg": "rgba(0, 230, 118, 0.1)", "border": "rgba(0, 230, 118, 0.3)", "text": "#00E676"},
        "blue": {"bg": "rgba(68, 138, 255, 0.1)", "border": "rgba(68, 138, 255, 0.3)", "text": "#448AFF"},
        "red": {"bg": "rgba(255, 82, 82, 0.1)", "border": "rgba(255, 82, 82, 0.3)", "text": "#FF5252"}
    }
    
    colors = color_map.get(color, color_map["gold"])
    
    card_html = f"""
    <div style="
        background: linear-gradient(135deg, {colors['bg']}, rgba(26, 35, 50, 0.5));
        border: 1px solid {colors['border']};
        border-left: 4px solid {colors['text']};
        border-radius: 16px;
        padding: 24px;
        margin: 10px 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
        animation: fadeIn 0.5s ease-in;
    ">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
            <span style="font-size: 2rem;">{icon}</span>
            <h3 style="color: {colors['text']}; margin: 0; font-size: 1rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">
                {title}
            </h3>
        </div>
        <div style="font-size: 2.5rem; font-weight: 700; color: #FFFFFF; margin: 8px 0;">
            {value}
        </div>
        {f'<div style="color: #B8C5D6; font-size: 0.9rem; margin-top: 8px;">{subtitle}</div>' if subtitle else ''}
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)