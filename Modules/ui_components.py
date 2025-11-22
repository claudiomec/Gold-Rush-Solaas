import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def load_custom_css():
    """Carrega o tema visual Gold Rush (Dark Mode)."""
    st.markdown("""
        <style>
        .stApp { background-color: #0E1117; }
        .block-container { padding-top: 1rem; padding-bottom: 1rem; }
        
        /* Sidebar */
        section[data-testid="stSidebar"] { background-color: #1C1E24; }
        section[data-testid="stSidebar"] * { color: #FFFFFF !important; }
        
        /* Tipografia */
        h1, h2, h3 { color: #FFD700 !important; }
        
        /* Cards KPI */
        div[data-testid="stMetric"] {
            background-color: #262730;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
        }
        div[data-testid="stMetricLabel"] { color: #FFD700 !important; font-size: 0.9rem !important; }
        div[data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 1.4rem !important; }
        
        /* Inputs */
        .stTextInput input, .stSelectbox div[data-baseweb="select"], .stMultiSelect div[data-baseweb="select"] { 
            background-color: #1C1E24 !important; color: white !important; border: 1px solid #444; 
        }
        
        /* Tabelas */
        div[data-testid="stDataFrame"] { background-color: #1C1E24; }
        .stRadio > label { display: none; }
        
        /* Cards Financeiros */
        .savings-card { background-color: #1C1E24; border-left: 5px solid #00CC96; padding: 15px; margin-bottom: 10px; border-radius: 5px; }
        .loss-card { background-color: #1C1E24; border-left: 5px solid #FF4B4B; padding: 15px; margin-bottom: 10px; border-radius: 5px; }
        
        /* Imagem de Login */
        div[data-testid="stImage"] {
            display: flex;
            justify-content: center;
        }
        </style>
    """, unsafe_allow_html=True)

def render_price_chart(df):
    """Renderiza o gráfico principal de preços com Matplotlib."""
    fig, ax = plt.subplots(figsize=(10, 3))
    fig.patch.set_facecolor('#0E1117')
    ax.set_facecolor('#0E1117')
    
    # Plotagem
    ax.plot(df.index, df['PP_Price'], color='#666', alpha=0.3, label='Spot Calculado', linewidth=1)
    ax.plot(df.index, df['Trend'], color='#FFD700', label='Tendência Gold Rush', linewidth=2.5)
    
    # Estilização
    ax.tick_params(axis='both', colors='#AAA', labelsize=8)
    for spine in ax.spines.values():
        spine.set_color('#333')
    ax.grid(True, alpha=0.1)
    ax.legend(facecolor='#1C1E24', labelcolor='white', fontsize=8, framealpha=1)
    
    st.pyplot(fig, use_container_width=True)

def render_insight_card(variation_pct):
    """Renderiza o card de recomendação (Compra/Espera)."""
    if variation_pct > 0.5:
        msg, cor = "⚠️ <b>ALTA:</b> Pressão de custos detectada. Antecipe compras.", "#FF4B4B"
    elif variation_pct < -0.5:
        msg, cor = "✅ <b>BAIXA:</b> Janela de oportunidade. Compre fracionado.", "#00CC96"
    else:
        msg, cor = "⚖️ <b>ESTÁVEL:</b> Mercado lateralizado. Mantenha programação.", "#FFAA00"

    st.markdown(f"""
    <div style='background-color: #1C1E24; padding: 10px; border-radius: 6px; border-left: 4px solid {cor}; color: #DDD; font-size: 0.9rem;'>
        {msg}
    </div>
    """, unsafe_allow_html=True)