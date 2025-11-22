from fpdf import FPDF
import pandas as pd
import matplotlib.pyplot as plt
import tempfile
import os

class PDFReport(FPDF):
    def header(self):
        # Logo / Título
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Gold Rush Analytics - Laudo Tecnico', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, 'Inteligencia de Mercado Industrial', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def generate_pdf_report(df, current_price, trend_pct, ocean, dollar, suggestion):
    """Gera o arquivo PDF e retorna os bytes."""
    
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font('Arial', '', 12)
    
    # 1. Resumo Executivo (Card)
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, 40, 190, 40, 'F')
    pdf.set_xy(15, 45)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, f"Preco Justo (SP): R$ {current_price:.2f} / kg", ln=1)
    
    pdf.set_font('Arial', '', 12)
    pdf.set_xy(15, 55)
    pdf.cell(0, 10, f"Tendencia (7d): {trend_pct:.2f}% | Dolar Base: R$ {dollar:.4f}", ln=1)
    
    pdf.set_xy(15, 65)
    if trend_pct > 0.5:
        pdf.set_text_color(200, 0, 0) # Vermelho
        status = "ALTA (Antecipar Compras)"
    elif trend_pct < -0.5:
        pdf.set_text_color(0, 150, 0) # Verde
        status = "BAIXA (Aguardar / Oportunidade)"
    else:
        pdf.set_text_color(200, 150, 0) # Laranja
        status = "ESTAVEL (Manter Programacao)"
        
    pdf.cell(0, 10, f"Recomendacao: {status}", ln=1)
    pdf.set_text_color(0, 0, 0) # Volta para preto
    
    pdf.ln(20)
    
    # 2. Gráfico de Tendência (Gerado via Matplotlib para o PDF)
    # Criamos uma figura temporária apenas para salvar a imagem
    plt.figure(figsize=(10, 4))
    plt.plot(df.index, df['PP_Price'], color='#999999', alpha=0.5, label='Spot Diario')
    plt.plot(df.index, df['Trend'], color='#FFD700', linewidth=2, label='Tendencia')
    plt.title('Historico de Preco (6 Meses)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
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

    # 3. Tabela de Dados Recentes
    pdf.set_y(200)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Ultimos 5 Dias (Detalhado)', ln=1)
    pdf.set_font('Arial', '', 10)
    
    # Cabeçalho da Tabela
    pdf.cell(40, 8, 'Data', 1)
    pdf.cell(40, 8, 'Preco Final (R$)', 1)
    pdf.cell(40, 8, 'WTI (USD)', 1)
    pdf.cell(40, 8, 'Cambio (R$)', 1)
    pdf.ln()
    
    # Linhas
    last_5 = df.tail(5).sort_index(ascending=False)
    for index, row in last_5.iterrows():
        pdf.cell(40, 8, index.strftime('%d/%m/%Y'), 1)
        pdf.cell(40, 8, f"{row['PP_Price']:.2f}", 1)
        pdf.cell(40, 8, f"{row['WTI']:.2f}", 1)
        pdf.cell(40, 8, f"{row['USD_BRL']:.4f}", 1)
        pdf.ln()
        
    # Disclaimer
    pdf.ln(10)
    pdf.set_font('Arial', 'I', 7)
    pdf.multi_cell(0, 5, "Este relatorio e gerado automaticamente com base em modelos estatisticos. A Gold Rush nao se responsabiliza por decisoes comerciais tomadas com base nestes dados.")
    
    # Retorna o binário do PDF
    return pdf.output(dest='S').encode('latin-1')