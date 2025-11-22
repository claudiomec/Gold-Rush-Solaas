import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import streamlit as st

def send_verification_email(to_email, verification_link):
    """
    Envia o e-mail de validação de conta com o link.
    Retorna: (bool, mensagem)
    """
    # Tenta pegar credenciais dos Secrets (Streamlit Cloud) ou Env (Local)
    try:
        if "SMTP_EMAIL" in st.secrets:
            smtp_user = st.secrets["SMTP_EMAIL"]
            smtp_pass = st.secrets["SMTP_PASSWORD"]
            smtp_server = st.secrets.get("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = int(st.secrets.get("SMTP_PORT", 587))
        else:
            # Fallback para variáveis de ambiente (caso rode fora do Streamlit)
            smtp_user = os.environ.get("SMTP_EMAIL")
            smtp_pass = os.environ.get("SMTP_PASSWORD")
            smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = int(os.environ.get("SMTP_PORT", 587))

        if not smtp_user or not smtp_pass:
            return False, "Configurações de SMTP não encontradas nos Segredos."

        # Montagem do E-mail
        msg = MIMEMultipart()
        msg['From'] = f"Gold Rush Security <{smtp_user}>"
        msg['To'] = to_email
        msg['Subject'] = "🔐 Valide seu acesso ao Gold Rush Analytics"

        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="background-color: #f4f4f4; padding: 20px; border-radius: 10px;">
                <h2 style="color: #FFD700; text-shadow: 1px 1px 1px #000;">Bem-vindo ao Gold Rush</h2>
                <p>Um administrador criou uma conta para você.</p>
                <p>Para ativar seu acesso e definir que este e-mail é realmente seu, clique no botão abaixo:</p>
                
                <br>
                <a href="{verification_link}" style="background-color: #00CC96; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">VALIDAR MEU E-MAIL</a>
                <br><br>
                
                <p style="font-size: 12px; color: #666;">Se o botão não funcionar, copie e cole este link no navegador:<br>
                {verification_link}</p>
                <hr>
                <p style="font-size: 12px; color: #999;">Se você não solicitou este acesso, ignore este e-mail.</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body_html, 'html'))

        # Envio
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        
        return True, "E-mail enviado com sucesso!"

    except Exception as e:
        return False, f"Erro no envio SMTP: {str(e)}"
    