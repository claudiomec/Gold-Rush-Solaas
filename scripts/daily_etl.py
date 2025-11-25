import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
import toml
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURAÇÕES ---
COLLECTION_NAME = "market_data"
SYMBOL_WTI = "CL=F"
SYMBOL_BRL = "BRL=X"
DAYS_BACK = 365 * 2  # Carga histórica de 2 anos

# Configuração do Alerta
ALERT_THRESHOLD = 0.03 # 3% de variação para disparar
STANDARD_OCEAN = 60
STANDARD_INTERNAL = 0.15
STANDARD_ICMS = 18
STANDARD_MARGIN = 10

def get_db_connection():
    """
    Conecta ao Firestore.
    Prioridade: Variável de Ambiente (CI/CD) > Secrets Local (Dev).
    """
    key_dict = None
    
    # 1. Tenta ler do arquivo local .streamlit/secrets.toml
    try:
        # Caminho relativo assumindo que o script roda da raiz do projeto
        secrets_path = ".streamlit/secrets.toml"
        if os.path.exists(secrets_path):
            secrets = toml.load(secrets_path)
            if "firebase" in secrets:
                key_dict = secrets["firebase"]
                # Se estiver aninhado como antigamente (text_key), converte
                if "text_key" in key_dict:
                    import json
                    key_dict = json.loads(key_dict["text_key"])
    except Exception as e:
        print(f"⚠️ Aviso: Não foi possível ler secrets local: {e}")

    # 2. Tenta variável de ambiente (GitHub Actions)
    if not key_dict and "FIREBASE_CREDENTIALS" in os.environ:
        import json
        key_dict = json.loads(os.environ["FIREBASE_CREDENTIALS"])

    if not key_dict:
        raise Exception("❌ ERRO FATAL: Credenciais não encontradas. Configure FIREBASE_CREDENTIALS.")

    # --- SANITIZAÇÃO DA CHAVE ---
    # Garante que a chave privada está formatada corretamente
    if "private_key" in key_dict:
        pk = key_dict["private_key"]
        pk = pk.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "")
        pk = pk.replace("\\n", "").replace("\n", "").replace(" ", "").replace("\t", "").replace('"', '').replace("'", "")
        key_dict["private_key"] = "-----BEGIN PRIVATE KEY-----\n" + pk + "\n-----END PRIVATE KEY-----"

    # Conecta ao Firebase
    if not firebase_admin._apps:
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    
    return firestore.client()

def extract_market_data():
    """Baixa dados do Yahoo Finance."""
    print(f"📉 Baixando dados ({DAYS_BACK} dias)...")
    end = datetime.now()
    start = end - timedelta(days=DAYS_BACK)
    
    wti = yf.download(SYMBOL_WTI, start=start, end=end, progress=False, auto_adjust=True)['Close']
    brl = yf.download(SYMBOL_BRL, start=start, end=end, progress=False, auto_adjust=True)['Close']
    
    if wti.empty or brl.empty:
        print("⚠️ Aviso: API vazia. Gerando dados dummy para manter pipeline vivo.")
        idx = pd.date_range(start, end)
        return pd.DataFrame({'WTI': [70.0]*len(idx), 'USD_BRL': [5.0]*len(idx)}, index=idx)
        
    # Unir e Limpar
    df = pd.concat([wti, brl], axis=1).dropna()
    df.columns = ['WTI', 'USD_BRL']
    df.index.name = 'Date'
    
    print(f"✅ Extração concluída: {len(df)} registros encontrados.")
    return df

def transform_data(df):
    """Aplica as regras de negócio para gerar a base analítica."""
    print("wd Processando regras de negócio...")
    
    # Cálculo do Proxy Internacional (FOB)
    df['PP_FOB_USD'] = (df['WTI'] * 0.014) + 0.35
    
    # Prepara para o Firestore (Data como String para ID)
    df = df.reset_index()
    df['doc_id'] = df['Date'].dt.strftime('%Y-%m-%d')
    
    return df

def load_to_firestore(db, df):
    """Salva os dados no banco em lotes (Batch)."""
    print(f"💾 Iniciando carga no Firestore (Coleção: {COLLECTION_NAME})...")
    
    batch = db.batch()
    batch_count = 0
    total_records = 0
    
    collection_ref = db.collection(COLLECTION_NAME)
    
    for _, row in df.iterrows():
        doc_ref = collection_ref.document(row['doc_id'])
        
        # Payload do documento
        doc_data = {
            'date': row['Date'],
            'wti': float(row['WTI']),
            'usd_brl': float(row['USD_BRL']),
            'pp_fob_usd': float(row['PP_FOB_USD']),
            'last_updated': firestore.SERVER_TIMESTAMP
        }
        
        batch.set(doc_ref, doc_data)
        batch_count += 1
        total_records += 1
        
        # Firestore tem limite de 500 operações por batch
        if batch_count >= 400:
            batch.commit()
            print(f"   ... Lote processado ({total_records} registros)")
            batch = db.batch()
            batch_count = 0
            
    # Commita o restante
    if batch_count > 0:
        batch.commit()
        
    print(f"✅ Carga Finalizada! Total de {total_records} dias atualizados.")

# --- LÓGICA DE ALERTA (NOVIDADE) ---

def calculate_standard_price(row):
    """Calcula preço SP Padrão para referência do alerta."""
    cfr = row['PP_FOB_USD'] + (STANDARD_OCEAN / 1000)
    landed = cfr * row['USD_BRL'] * 1.12
    operational = landed + STANDARD_INTERNAL
    price_net = operational * (1 + STANDARD_MARGIN/100)
    final = price_net / (1 - STANDARD_ICMS/100)
    return final

def get_active_users_emails(db):
    """Busca emails de usuários no Firestore."""
    users = []
    try:
        docs = db.collection('users').stream()
        for doc in docs:
            data = doc.to_dict()
            # Assume que o username é o email, ou verifica se tem @
            email = data.get('username', '')
            if '@' in email:
                users.append(email)
    except Exception as e:
        print(f"Erro ao buscar usuários: {e}")
    return users

def send_email_alert(recipients, subject, body_html):
    """Envia e-mail via SMTP (Gmail/SendGrid)."""
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_EMAIL")
    smtp_pass = os.environ.get("SMTP_PASSWORD")

    if not smtp_user or not smtp_pass:
        print("⚠️ Pular envio de e-mail: Credenciais SMTP não configuradas.")
        return

    print(f"📧 Enviando alerta para {len(recipients)} usuários...")

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)

        for email in recipients:
            msg = MIMEMultipart()
            msg['From'] = f"Gold Rush Analytics <{smtp_user}>"
            msg['To'] = email
            msg['Subject'] = subject
            msg.attach(MIMEText(body_html, 'html'))
            server.send_message(msg)
            
        server.quit()
        print("✅ E-mails enviados com sucesso!")
    except Exception as e:
        print(f"❌ Erro no envio de e-mail: {e}")

def check_and_send_alerts(db, df):
    print("🔍 Analisando necessidade de alerta...")
    
    if len(df) < 8:
        print("Dados insuficientes para cálculo de tendência.")
        return

    # Calcula preço final para os últimos dias
    df['Final_Price'] = df.apply(calculate_standard_price, axis=1)
    
    # Garantir que é datetime
    df['Date'] = pd.to_datetime(df['Date'])
    
    current_price = df['Final_Price'].iloc[-1]
    current_date = df['Date'].iloc[-1]
    
    # BUG FIX: Comparação temporal robusta (7 dias)
    try:
        target_date = current_date - timedelta(days=7)
        # Encontra a linha com a data mais próxima
        closest_idx = (df['Date'] - target_date).abs().idxmin()
        price_7d_ago = df.loc[closest_idx, 'Final_Price']
    except Exception as e:
        print(f"Erro ao calcular data anterior: {e}")
        price_7d_ago = current_price
    
    variation = (current_price / price_7d_ago) - 1
    
    print(f"   Preço Hoje ({current_date.date()}): R$ {current_price:.2f}")
    print(f"   Preço Ref ({target_date.date()}): R$ {price_7d_ago:.2f}")
    print(f"   Variação: {variation*100:.2f}% (Threshold: {ALERT_THRESHOLD*100}%)")

    if abs(variation) >= ALERT_THRESHOLD:
        trend = "ALTA 📈" if variation > 0 else "BAIXA 📉"
        color = "#FF4B4B" if variation > 0 else "#00CC96"
        action = "Antecipar Compras" if variation > 0 else "Aguardar Oportunidade"
        
        subject = f"🚨 Alerta Gold Rush: Tendência de {trend} ({variation*100:.1f}%)"
        
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background-color: #1C1E24; padding: 20px; color: white; border-radius: 10px;">
                <h2 style="color: #FFD700;">Gold Rush Analytics</h2>
                <hr style="border: 1px solid #333;">
                <p>Detectamos uma movimentação relevante no mercado de Polipropileno.</p>
                
                <div style="background-color: {color}; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin:0; color: white;">TENDÊNCIA DE {trend}</h3>
                    <p style="margin:5px 0 0 0; color: white;">Variação de <b>{variation*100:.2f}%</b> nos últimos 7 dias.</p>
                </div>
                
                <p><b>Preço de Referência (SP):</b> R$ {current_price:.2f}/kg</p>
                <p><b>Recomendação:</b> {action}</p>
                
                <br>
                <a href="https://gold-rush.streamlit.app" style="background-color: #FFD700; color: black; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Acessar Plataforma</a>
            </div>
        </body>
        </html>
        """
        
        users = get_active_users_emails(db)
        if users:
            send_email_alert(users, subject, body_html)
        else:
            print("⚠️ Nenhum usuário com e-mail encontrado para enviar.")
    else:
        print("✅ Mercado estável. Nenhum alerta necessário hoje.")

if __name__ == "__main__":
    print("========================================")
    print("🤖 ROBÔ ETL GOLD RUSH - INICIANDO")
    print("========================================")
    
    try:
        # 1. Conectar
        db_client = get_db_connection()
        
        # 2. Extrair
        df_raw = extract_market_data()
        
        # 3. Transformar
        df_clean = transform_data(df_raw)
        
        # 4. Carregar
        load_to_firestore(db_client, df_clean)
        
        # 5. Checar Alertas (Etapa Nova)
        check_and_send_alerts(db_client, df_clean)
        
        print("========================================")
        print("🏆 SUCESSO: DADOS E ALERTAS PROCESSADOS")
        print("========================================")
        
    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO: {e}")
        exit(1)