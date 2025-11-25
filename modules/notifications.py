"""
Módulo de Notificações - Sistema de alertas e notificações in-app
"""
import streamlit as st
from datetime import datetime, timedelta
from modules.database import get_db
import streamlit_antd_components as sac

def add_notification(user_id, title, message, type="info", priority="normal"):
    """
    Adiciona uma notificação para um usuário.
    
    Args:
        user_id: ID do usuário
        title: Título da notificação
        message: Mensagem da notificação
        type: Tipo (info, success, warning, error)
        priority: Prioridade (low, normal, high)
    """
    db = get_db()
    if not db:
        return False
    
    try:
        notifications_ref = db.collection('notifications')
        notifications_ref.add({
            'user_id': user_id,
            'title': title,
            'message': message,
            'type': type,
            'priority': priority,
            'read': False,
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(days=30)  # Expira em 30 dias
        })
        return True
    except Exception as e:
        print(f"Erro ao adicionar notificação: {e}")
        return False

def get_user_notifications(user_id, unread_only=False, limit=10):
    """
    Busca notificações do usuário.
    
    Args:
        user_id: ID do usuário
        unread_only: Se True, retorna apenas não lidas
        limit: Limite de notificações
        
    Returns:
        Lista de notificações
    """
    db = get_db()
    if not db:
        return []
    
    try:
        notifications_ref = db.collection('notifications')
        query = notifications_ref.where('user_id', '==', user_id)
        
        if unread_only:
            query = query.where('read', '==', False)
        
        query = query.order_by('created_at', direction='DESCENDING').limit(limit)
        
        notifications = []
        for doc in query.stream():
            notif_data = doc.to_dict()
            notif_data['id'] = doc.id
            # Converte timestamps do Firestore
            if 'created_at' in notif_data and hasattr(notif_data['created_at'], 'timestamp'):
                notif_data['created_at'] = datetime.fromtimestamp(notif_data['created_at'].timestamp())
            notifications.append(notif_data)
        
        return notifications
    except Exception as e:
        print(f"Erro ao buscar notificações: {e}")
        return []

def mark_as_read(notification_id):
    """Marca uma notificação como lida."""
    db = get_db()
    if not db:
        return False
    
    try:
        db.collection('notifications').document(notification_id).update({'read': True})
        return True
    except Exception as e:
        print(f"Erro ao marcar notificação como lida: {e}")
        return False

def mark_all_as_read(user_id):
    """Marca todas as notificações do usuário como lidas."""
    db = get_db()
    if not db:
        return False
    
    try:
        notifications = get_user_notifications(user_id, unread_only=True)
        for notif in notifications:
            mark_as_read(notif['id'])
        return True
    except Exception as e:
        print(f"Erro ao marcar todas como lidas: {e}")
        return False

def get_unread_count(user_id):
    """Retorna o número de notificações não lidas."""
    notifications = get_user_notifications(user_id, unread_only=True, limit=100)
    return len(notifications)

def render_notification_bell():
    """Renderiza o ícone de sino de notificações na sidebar."""
    user_id = st.session_state.get('user_name')
    if not user_id:
        return
    
    unread_count = get_unread_count(user_id)
    
    if unread_count > 0:
        st.markdown(f"""
            <div style="
                position: relative;
                display: inline-block;
                margin-bottom: 1rem;
            ">
                <button onclick="window.location.href='?page=notifications'" style="
                    background: linear-gradient(135deg, rgba(255, 215, 0, 0.2), rgba(255, 165, 0, 0.1));
                    border: 1px solid rgba(255, 215, 0, 0.3);
                    border-radius: 10px;
                    padding: 10px;
                    width: 100%;
                    cursor: pointer;
                    color: #FFD700;
                    font-size: 1.2rem;
                ">
                    🔔 Notificações
                    <span style="
                        background: #FF5252;
                        color: white;
                        border-radius: 50%;
                        padding: 2px 8px;
                        font-size: 0.75rem;
                        margin-left: 8px;
                    ">{unread_count}</span>
                </button>
            </div>
        """, unsafe_allow_html=True)

def render_notifications_page():
    """Renderiza a página de notificações."""
    user_id = st.session_state.get('user_name')
    if not user_id:
        st.warning("Você precisa estar logado para ver notificações.")
        return
    
    st.title("🔔 Notificações")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("✅ Marcar todas como lidas", use_container_width=True):
            if mark_all_as_read(user_id):
                st.success("Todas as notificações foram marcadas como lidas!")
                st.rerun()
    
    notifications = get_user_notifications(user_id, limit=50)
    
    if not notifications:
        st.info("📭 Nenhuma notificação no momento.")
        return
    
    unread_notifications = [n for n in notifications if not n.get('read', False)]
    read_notifications = [n for n in notifications if n.get('read', False)]
    
    if unread_notifications:
        st.markdown("### 📬 Não Lidas")
        for notif in unread_notifications:
            render_notification_card(notif, user_id)
    
    if read_notifications:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📭 Lidas")
        for notif in read_notifications:
            render_notification_card(notif, user_id, is_read=True)

def render_notification_card(notification, user_id, is_read=False):
    """Renderiza um card de notificação."""
    notif_id = notification.get('id')
    title = notification.get('title', 'Sem título')
    message = notification.get('message', '')
    notif_type = notification.get('type', 'info')
    created_at = notification.get('created_at', datetime.now())
    
    if isinstance(created_at, datetime):
        time_str = created_at.strftime("%d/%m/%Y %H:%M")
    else:
        time_str = "Agora"
    
    # Cores por tipo
    color_map = {
        'info': '#448AFF',
        'success': '#00E676',
        'warning': '#FFA500',
        'error': '#FF5252'
    }
    bg_color = color_map.get(notif_type, '#448AFF')
    
    opacity = "0.6" if is_read else "1.0"
    
    st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, rgba(26, 35, 50, 0.95), rgba(20, 27, 45, 0.95));
            border-left: 4px solid {bg_color};
            border: 1px solid rgba(255, 215, 0, 0.2);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            opacity: {opacity};
        ">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div style="flex: 1;">
                    <h4 style="color: {bg_color}; margin: 0 0 0.5rem 0; font-size: 1.1rem;">
                        {title}
                    </h4>
                    <p style="color: #B8C5D6; margin: 0 0 0.5rem 0; font-size: 0.9rem;">
                        {message}
                    </p>
                    <span style="color: #999; font-size: 0.75rem;">{time_str}</span>
                </div>
                {f'<button onclick="markRead_{notif_id}()" style="background: transparent; border: none; color: #999; cursor: pointer; font-size: 1.2rem;">✓</button>' if not is_read else ''}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if not is_read and notif_id:
        # Botão para marcar como lida
        if st.button("Marcar como lida", key=f"read_{notif_id}"):
            if mark_as_read(notif_id):
                st.rerun()

def create_price_alert(user_id, target_price, direction="below"):
    """
    Cria um alerta de preço.
    
    Args:
        user_id: ID do usuário
        target_price: Preço alvo
        direction: "below" ou "above"
    """
    direction_text = "abaixo de" if direction == "below" else "acima de"
    title = f"Alerta de Preço: {direction_text} R$ {target_price:.2f}"
    message = f"O preço atingiu {direction_text} R$ {target_price:.2f}. Verifique o monitor para mais detalhes."
    
    return add_notification(user_id, title, message, type="warning", priority="high")

