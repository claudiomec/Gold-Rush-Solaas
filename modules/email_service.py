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
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; background-color: #f5f5f5;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 40px 20px;">
                <tr>
                    <td align="center">
                        <table width="600" cellpadding="0" cellspacing="0" style="background: linear-gradient(135deg, #0A0E1A 0%, #141B2D 100%); border-radius: 16px; overflow: hidden; box-shadow: 0 8px 32px rgba(0,0,0,0.2);">
                            <!-- Header -->
                            <tr>
                                <td style="background: linear-gradient(135deg, rgba(255, 215, 0, 0.2), rgba(255, 165, 0, 0.1)); padding: 40px 30px; text-align: center; border-bottom: 2px solid rgba(255, 215, 0, 0.3);">
                                    <h1 style="margin: 0; color: #FFD700; font-size: 32px; font-weight: 700; text-shadow: 0 0 20px rgba(255, 215, 0, 0.3);">
                                        🏭 Gold Rush Analytics
                                    </h1>
                                    <p style="margin: 10px 0 0 0; color: #B8C5D6; font-size: 14px;">Sistema de Monitoramento Industrial</p>
                                </td>
                            </tr>
                            
                            <!-- Content -->
                            <tr>
                                <td style="padding: 40px 30px; color: #E0E0E0;">
                                    <h2 style="margin: 0 0 20px 0; color: #FFD700; font-size: 24px; font-weight: 600;">
                                        Bem-vindo ao Gold Rush! 👋
                                    </h2>
                                    
                                    <p style="margin: 0 0 20px 0; font-size: 16px; line-height: 1.6; color: #B8C5D6;">
                                        Um administrador criou uma conta para você no sistema Gold Rush Analytics.
                                    </p>
                                    
                                    <p style="margin: 0 0 30px 0; font-size: 16px; line-height: 1.6; color: #B8C5D6;">
                                        Para ativar seu acesso e garantir a segurança da sua conta, clique no botão abaixo para validar seu e-mail:
                                    </p>
                                    
                                    <!-- CTA Button -->
                                    <table width="100%" cellpadding="0" cellspacing="0">
                                        <tr>
                                            <td align="center" style="padding: 20px 0;">
                                                <a href="{verification_link}" style="display: inline-block; background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%); color: #000; padding: 16px 32px; text-decoration: none; border-radius: 12px; font-weight: 700; font-size: 16px; box-shadow: 0 4px 15px rgba(255, 215, 0, 0.4); transition: all 0.3s;">
                                                    ✅ VALIDAR MEU E-MAIL
                                                </a>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <!-- Alternative Link -->
                                    <div style="margin-top: 30px; padding: 20px; background: rgba(255, 255, 255, 0.05); border-radius: 8px; border-left: 4px solid #FFD700;">
                                        <p style="margin: 0 0 10px 0; font-size: 12px; color: #999; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">
                                            Link Alternativo
                                        </p>
                                        <p style="margin: 0; font-size: 12px; color: #B8C5D6; word-break: break-all;">
                                            {verification_link}
                                        </p>
                                    </div>
                                </td>
                            </tr>
                            
                            <!-- Footer -->
                            <tr>
                                <td style="padding: 30px; background: rgba(0, 0, 0, 0.3); border-top: 1px solid rgba(255, 215, 0, 0.1); text-align: center;">
                                    <p style="margin: 0 0 10px 0; font-size: 12px; color: #999;">
                                        Se você não solicitou este acesso, pode ignorar este e-mail com segurança.
                                    </p>
                                    <p style="margin: 0; font-size: 11px; color: #666;">
                                        © {__import__('datetime').datetime.now().year} Gold Rush Analytics. Todos os direitos reservados.
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
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
    