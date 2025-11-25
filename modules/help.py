"""
Módulo de Help e Documentação - Tooltips, FAQ e guias
"""
import streamlit as st

def render_tooltip(text, help_text):
    """Renderiza um tooltip ao lado de um elemento."""
    st.markdown(f"""
        <div style="position: relative; display: inline-block;">
            <span style="cursor: help; color: #FFD700;">{text}</span>
            <div class="tooltip" style="
                visibility: hidden;
                width: 200px;
                background-color: rgba(26, 35, 50, 0.95);
                color: #B8C5D6;
                text-align: center;
                border-radius: 6px;
                padding: 8px;
                position: absolute;
                z-index: 1;
                bottom: 125%;
                left: 50%;
                margin-left: -100px;
                border: 1px solid rgba(255, 215, 0, 0.3);
            ">
                {help_text}
            </div>
        </div>
    """, unsafe_allow_html=True)

def render_help_button():
    """Renderiza botão de ajuda flutuante."""
    st.markdown("""
        <style>
        .help-button {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: linear-gradient(135deg, #FFD700, #FFA500);
            color: #000;
            border: none;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            font-size: 24px;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(255, 215, 0, 0.4);
            z-index: 1000;
            transition: all 0.3s ease;
        }
        .help-button:hover {
            transform: scale(1.1);
            box-shadow: 0 6px 20px rgba(255, 215, 0, 0.6);
        }
        </style>
        <button class="help-button" onclick="document.getElementById('help-modal').style.display='block'">
            ?
        </button>
    """, unsafe_allow_html=True)

def render_faq():
    """Renderiza seção de FAQ."""
    st.markdown("### ❓ Perguntas Frequentes")
    
    faqs = [
        {
            "pergunta": "Como o sistema calcula o preço justo?",
            "resposta": "O preço justo é calculado com base em múltiplos fatores: preço FOB do commodity, frete marítimo, taxa de câmbio, ICMS, frete interno e margem de lucro. Utilizamos modelos estatísticos para determinar a tendência de mercado."
        },
        {
            "pergunta": "Com que frequência os dados são atualizados?",
            "resposta": "Os dados de mercado são atualizados diariamente através de nosso processo ETL automatizado. Os preços refletem as condições mais recentes do mercado."
        },
        {
            "pergunta": "Como interpretar a tendência de preços?",
            "resposta": "A tendência mostra a variação percentual dos últimos 7 dias. Valores positivos acima de 0.5% indicam alta (considere antecipar compras), valores negativos abaixo de -0.5% indicam baixa (oportunidade), e valores entre -0.5% e 0.5% indicam mercado estável."
        },
        {
            "pergunta": "Posso exportar os dados?",
            "resposta": "Sim! Você pode exportar os dados em formato Excel através da seção 'Dados (XLSX)' no menu. Também é possível baixar relatórios em PDF diretamente do Monitor."
        },
        {
            "pergunta": "Como configurar alertas de preço?",
            "resposta": "Os alertas são configurados automaticamente quando há mudanças significativas no mercado. Você receberá notificações quando o preço atingir valores críticos. Em breve, permitiremos configuração personalizada de alertas."
        }
    ]
    
    for i, faq in enumerate(faqs):
        with st.expander(f"**{faq['pergunta']}**", expanded=False):
            st.markdown(faq['resposta'])

def render_quick_guide():
    """Renderiza guia rápido de uso."""
    st.markdown("### 🚀 Guia Rápido")
    
    st.markdown("""
    #### 📊 Dashboard
    - Visualize métricas principais e KPIs
    - Acompanhe a evolução de preços
    - Veja análise de economia potencial
    
    #### 📈 Monitor
    - Ajuste parâmetros de cálculo (frete, ICMS, margem)
    - Visualize gráficos interativos de tendência
    - Baixe relatórios em PDF
    
    #### 💰 Calculadora Financeira
    - Compare preço pago vs preço justo
    - Calcule economia ou perda potencial
    - Analise impacto por volume
    
    #### 🔔 Notificações
    - Receba alertas de mudanças de mercado
    - Acompanhe recomendações importantes
    - Configure preferências de notificação
    """)

def render_help_modal():
    """Renderiza modal de ajuda."""
    st.markdown("""
        <div id="help-modal" style="
            display: none;
            position: fixed;
            z-index: 10000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.7);
        ">
            <div style="
                background: linear-gradient(135deg, #1A2332, #141B2D);
                margin: 5% auto;
                padding: 20px;
                border: 1px solid rgba(255, 215, 0, 0.3);
                width: 80%;
                max-width: 600px;
                border-radius: 16px;
            ">
                <h2 style="color: #FFD700;">Ajuda e Suporte</h2>
                <p style="color: #B8C5D6;">Conteúdo de ajuda aqui...</p>
                <button onclick="document.getElementById('help-modal').style.display='none'">Fechar</button>
            </div>
        </div>
    """, unsafe_allow_html=True)

