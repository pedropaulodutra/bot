
import requests

def enviar_notificacao(mensagem: str, token: str, chat_id: str) -> bool:
    """
    Envia uma notificação para um usuário específico do Telegram.

    Args:
        mensagem (str): O texto da mensagem a ser enviada.
        token (str): O token do Bot do Telegram do usuário.
        chat_id (str): O Chat ID do Telegram do usuário.

    Returns:
        bool: True se a mensagem foi enviada com sucesso, False caso contrário.
    """
    # Validação para garantir que as credenciais foram passadas
    if not token or not chat_id:
        print("ERRO DE NOTIFICAÇÃO: Token ou Chat ID do Telegram não foram fornecidos.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': mensagem,
        'parse_mode': 'Markdown'
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200 and response.json().get("ok"):
            print("Mensagem enviada para o Telegram.")
            return True
        else:
            print(f"Erro ao enviar para Telegram: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão ao enviar para o Telegram: {e}")
        return False
