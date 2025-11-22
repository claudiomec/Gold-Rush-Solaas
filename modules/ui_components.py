import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import streamlit_antd_components as sac

def load_custom_css():
    """Carrega o tema visual Gold Rush (Dark Mode Refinado)."""
    st.markdown("""
        <style>
        /* Fundo Geral */
        .stApp { background-color: #0E1117; }
        
        /* Ajustes de Espaçamento */
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        
        /* Sidebar mais escura */
        section[data-testid="stSidebar"] { background-color: #15171C; }
        
        /* Títulos e Textos */
        h1, h2, h3 { color: #FFD700 !important; font-family: 'Helvetica Neue', sans-serif; }
        p, label, span { color: #E0E0E0 !important; }
        
        /* Cards de Métricas (KPIs) */
        div[data-testid="stMetric"] {
            background-color: #1F2329;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        div[data-testid="stMetricLabel"] { color: #FFD700 !important; font-weight: bold; }
        div[data-testid="stMetricValue"] { color: #FFFFFF !important; }
        
        /* Imagem de Login */
        div[data-testid="stImage"] { display: flex; justify-content: center; }
        
        /* Cards Financeiros Customizados */
        .savings-card { 
            background: linear-gradient(45deg, #1C1E24, #152e26); 
            border-left: 5px solid #00CC96; 
            padding: 20px; 
            border-radius: 8px; 
        }
        .loss-card { 
            background: linear-gradient(45deg, #1C1E24, #2e1515); 
            border-left: 5px solid #FF4B4B; 
            padding: 20px; 
            border-radius: 8px; 
        }
        </style>
    """, unsafe_allow_html=True)

def render_sidebar_menu(role, current_modules):
    """Renderiza o menu lateral moderno (Ant Design)."""
    
    # Ícones: https://icons.getbootstrap.com/
    
    if role == "admin":
        # Menu Completo de Admin
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
        ], index=0, format_func='title', size='middle', color='yellow')
        
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
    """Renderiza gráfico interativo com Plotly (Substitui Matplotlib)."""
    
    # Cria o objeto de figura interativa
    fig = go.Figure()

    # Linha do Preço Spot (Cinza)
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['PP_Price'],
        mode='lines',
        name='Spot Diário',
        line=dict(color='#666666', width=1),
        opacity=0.5
    ))

    # Linha da Tendência (Dourada e Grossa)
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['Trend'],
        mode='lines',
        name='Tendência Gold Rush',
        line=dict(color='#FFD700', width=4)
    ))

    # Layout Profissional (Dark Theme)
    fig.update_layout(
        title="",
        paper_bgcolor='rgba(0,0,0,0)', # Fundo transparente
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#E0E0E0'),
        margin=dict(l=20, r=20, t=20, b=20),
        height=350,
        showlegend=True,
        legend=dict(
            yanchor="top", y=0.99, xanchor="left", x=0.01,
            bgcolor="rgba(0,0,0,0.5)"
        ),
        hovermode="x unified" # Hover mostra todos os dados da data
    )
    
    # Eixos
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#333333')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#333333', tickprefix="R$ ")

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

def render_insight_card(variation_pct):
    """Renderiza o alerta usando componentes SAC."""
    if variation_pct > 0.5:
        sac.alert(
            label='TENDÊNCIA DE ALTA', 
            description='Pressão de custos detectada. Recomendamos antecipar compras.',
            size='lg', radius=True, icon=True, color='error', banner=False
        )
    elif variation_pct < -0.5:
        sac.alert(
            label='JANELA DE OPORTUNIDADE', 
            description='Tendência de queda. Compre fracionado ou aguarde.',
            size='lg', radius=True, icon=True, color='success', banner=False
        )
    else:
        sac.alert(
            label='MERCADO ESTÁVEL', 
            description='Sem grandes oscilações no curto prazo. Mantenha a programação.',
            size='lg', radius=True, icon=True, color='warning', banner=False
        )