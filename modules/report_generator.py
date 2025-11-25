from fpdf import FPDF
import pandas as pd
import matplotlib.pyplot as plt
import tempfile
import os

class PDFReport(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(15, 20, 15)
        
    def header(self):
        # Cabeçalho com gradiente simulado (retângulo dourado)
        self.set_fill_color(255, 215, 0)  # Dourado
        self.rect(0, 0, 210, 30, 'F')
        
        # Título principal
        self.set_xy(0, 8)
        self.set_font('Arial', 'B', 18)
        self.set_text_color(0, 0, 0)  # Preto sobre dourado
        self.cell(0, 10, 'Gold Rush Analytics', 0, 1, 'C')
        
        # Subtítulo
        self.set_font('Arial', 'I', 11)
        self.cell(0, 8, 'Inteligencia de Mercado Industrial', 0, 1, 'C')
        
        # Linha separadora
        self.set_fill_color(200, 200, 200)
        self.rect(10, 32, 190, 0.5, 'F')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f'Pagina {self.page_no()} | Gold Rush Analytics - Relatorio Gerado Automaticamente', 0, 0, 'C')
    
    def colored_box(self, x, y, w, h, r, g, b, text="", font_size=12, bold=False):
        """Cria uma caixa colorida com texto."""
        self.set_fill_color(r, g, b)
        self.rect(x, y, w, h, 'F')
        if text:
            self.set_xy(x + 5, y + (h - font_size) / 2)
            self.set_font('Arial', 'B' if bold else '', font_size)
            self.set_text_color(255, 255, 255)  # Texto branco
            self.cell(0, 0, text)
            self.set_text_color(0, 0, 0)  # Volta para preto

def generate_pdf_report(df, current_price, trend_pct, ocean, dollar, suggestion):
    """Gera o arquivo PDF profissional e retorna os bytes."""
    from datetime import datetime
    
    pdf = PDFReport()
    pdf.add_page()
    
    # Data do relatório
    pdf.set_font('Arial', 'I', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, f"Relatorio gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, 'R')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    
    # 1. Resumo Executivo (Card Moderno)
    pdf.set_fill_color(26, 35, 50)  # Fundo escuro
    pdf.rect(10, 45, 190, 50, 'F')
    
    # Título do card
    pdf.set_xy(15, 50)
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(255, 215, 0)  # Dourado
    pdf.cell(0, 10, "RESUMO EXECUTIVO", ln=1)
    
    # Preço principal
    pdf.set_xy(15, 60)
    pdf.set_font('Arial', 'B', 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, f"R$ {current_price:.2f} / kg", ln=1)
    
    # Informações secundárias
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(200, 200, 200)
    pdf.set_xy(15, 72)
    pdf.cell(0, 8, f"Tendencia (7 dias): {trend_pct:+.2f}%", ln=1)
    pdf.set_xy(15, 80)
    pdf.cell(0, 8, f"Dolar Base: R$ {dollar:.4f} | Frete Maritimo: USD {ocean}", ln=1)
    
    # Recomendação com cor
    pdf.set_xy(15, 88)
    if trend_pct > 0.5:
        pdf.set_text_color(255, 82, 82)  # Vermelho
        status = "ALTA - Recomendamos antecipar compras"
        icon = "📈"
    elif trend_pct < -0.5:
        pdf.set_text_color(0, 230, 118)  # Verde
        status = "BAIXA - Oportunidade de compra"
        icon = "📉"
    else:
        pdf.set_text_color(255, 165, 0)  # Laranja
        status = "ESTAVEL - Manter programacao"
        icon = "➡️"
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, f"{icon} {status}", ln=1)
    pdf.set_text_color(0, 0, 0)  # Volta para preto
    
    pdf.ln(20)
    
    # 2. Gráfico de Tendência (Gerado via Matplotlib para o PDF)
    # Criamos uma figura temporária apenas para salvar a imagem
    plt.figure(figsize=(10, 5))
    plt.style.use('dark_background')
    ax = plt.gca()
    ax.set_facecolor('#0A0E1A')
    fig = plt.gcf()
    fig.patch.set_facecolor('#0A0E1A')
    
    # Plot das linhas
    plt.plot(df.index, df['PP_Price'], color='#9E9E9E', alpha=0.7, linewidth=1.5, label='Preco Spot')
    if 'Trend' in df.columns:
        plt.plot(df.index, df['Trend'], color='#FFD700', linewidth=3, label='Tendencia Gold Rush')
    
    plt.title('Historico de Preco - Gold Rush Analytics', fontsize=14, color='#FFD700', fontweight='bold', pad=15)
    plt.xlabel('Data', color='#B8C5D6', fontsize=10)
    plt.ylabel('Preco (R$ / kg)', color='#B8C5D6', fontsize=10)
    plt.grid(True, alpha=0.2, color='#333333')
    plt.legend(loc='best', facecolor='#1A2332', edgecolor='#FFD700', labelcolor='#B8C5D6')
    ax.tick_params(colors='#B8C5D6')
    ax.spines['bottom'].set_color('#FFD700')
    ax.spines['top'].set_color('#FFD700')
    ax.spines['right'].set_color('#FFD700')
    ax.spines['left'].set_color('#FFD700')
    
    # Salva imagem temporária
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
        plt.savefig(tmpfile.name, dpi=100, bbox_inches='tight')
        pdf.image(tmpfile.name, x=10, y=90, w=190)
        temp_img_path = tmpfile.name
    
    # Limpa a imagem temporária
    try:
        os.remove(temp_img_path)
    except:
        pass

    # 3. Tabela de Dados Recentes (Melhorada)
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(255, 215, 0)
    pdf.cell(0, 10, 'DADOS RECENTES (Ultimos 5 Dias)', ln=1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)
    
    # Cabeçalho da Tabela (com fundo colorido)
    pdf.set_fill_color(255, 215, 0)  # Dourado
    pdf.set_text_color(0, 0, 0)  # Preto
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(42, 10, 'Data', 1, 0, 'C', True)
    pdf.cell(42, 10, 'Preco Final (R$)', 1, 0, 'C', True)
    pdf.cell(42, 10, 'WTI (USD)', 1, 0, 'C', True)
    pdf.cell(42, 10, 'Cambio (R$)', 1, 0, 'C', True)
    pdf.ln()
    
    # Linhas da tabela (alternando cores)
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(0, 0, 0)
    last_5 = df.tail(5).sort_index(ascending=False)
    
    for i, (index, row) in enumerate(last_5.iterrows()):
        # Alterna cor de fundo
        if i % 2 == 0:
            pdf.set_fill_color(245, 245, 245)
        else:
            pdf.set_fill_color(255, 255, 255)
        
        pdf.cell(42, 8, index.strftime('%d/%m/%Y'), 1, 0, 'C', True)
        pdf.cell(42, 8, f"{row['PP_Price']:.2f}", 1, 0, 'C', True)
        pdf.cell(42, 8, f"{row.get('WTI', 0):.2f}", 1, 0, 'C', True)
        pdf.cell(42, 8, f"{row['USD_BRL']:.4f}", 1, 0, 'C', True)
        pdf.ln()
        
    # Disclaimer melhorado
    pdf.ln(15)
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, pdf.get_y(), 190, 20, 'F')
    pdf.set_xy(12, pdf.get_y() + 3)
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(186, 4, "Este relatorio e gerado automaticamente com base em modelos estatisticos e dados de mercado publicos. A Gold Rush Analytics nao se responsabiliza por decisoes comerciais tomadas exclusivamente com base nestes dados. Sempre consulte profissionais qualificados para decisoes importantes.")
    
    # Retorna o binário do PDF
    return pdf.output(dest='S').encode('latin-1')