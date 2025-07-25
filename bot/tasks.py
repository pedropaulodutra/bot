import time
from celery import shared_task
from django.contrib.auth.models import User
from .models import BotControl
from .bot_logic import TradingBot
from .telegram import enviar_notificacao

@shared_task
def trading_bot_task(user_id):
    """
    Esta é a tarefa que o Celery executa em segundo plano para um usuário específico.
    Ela gerencia o ciclo de vida do bot daquele usuário.
    """
    # 1. Busca o usuário e suas configurações no banco de dados.
    try:
        user = User.objects.get(id=user_id)
        # Busca o BotControl daquele usuário específico
        control = BotControl.objects.get(user=user)
        # Busca o perfil com as chaves de API e credenciais do Telegram
        user_profile = user.userprofile 
    except (User.DoesNotExist, BotControl.DoesNotExist, User.userprofile.RelatedObjectDoesNotExist):
        print(f"Usuário com ID {user_id} ou seu Perfil/BotControl não foi encontrado. A tarefa não pode continuar.")
        return

    # 2. Validação: Verifica se as credenciais necessárias existem antes de começar.
    if not user_profile.api_key or not user_profile.api_secret:
        print(f"Usuário {user.username} não tem chaves de API. Encerrando tarefa.")
        # Opcional: Enviar notificação de erro se as credenciais do Telegram existirem
        if user_profile.telegram_chat_id:
             enviar_notificacao(
                "⚠️ *Falha ao Iniciar o Bot*\n\nVocê precisa configurar suas chaves de API no painel de Admin para iniciar o bot.",
                user_profile.telegram_bot_token, # Assumindo que você adicionou telegram_bot_token ao UserProfile
                user_profile.telegram_chat_id
            )
        # Marca o bot como parado no banco de dados por segurança
        control.is_running = False
        control.save()
        return

    # 3. Cria uma instância da sua lógica de bot, passando as configurações.
    bot_instance = TradingBot(control, user_profile)
    
    # Envia notificação de início usando as credenciais do usuário
    enviar_notificacao(
        f"🤖 [{bot_instance.symbol}] *Bot INICIADO*\nIniciando monitoramento...",
        user_profile.telegram_bot_token,
        user_profile.telegram_chat_id
    )
    print(f"--- Iniciando loop do bot para o usuário {user.username} no símbolo {control.symbol} ---")

    # 4. O loop principal do bot.
    while control.is_running:
        try:
            # Executa uma única verificação da estratégia.
            bot_instance.run_single_check()
        except Exception as e:
            print(f"ERRO CRÍTICO NO LOOP PRINCIPAL DA TAREFA para {user.username}: {e}")
            enviar_notificacao(
                f"🔥 *Erro Crítico no Bot* 🔥\nSímbolo: `{bot_instance.symbol}`\nErro: `{e}`\nO bot foi parado por segurança.",
                user_profile.telegram_bot_token,
                user_profile.telegram_chat_id
            )
            # Em caso de erro grave, desliga o bot
            control.is_running = False
            control.save()

        # 5. Pausa antes da próxima verificação.
        sleep_time = 60 # segundos
        print(f"Aguardando {sleep_time} segundos para a próxima checagem...")
        
        # Este loop interno permite um desligamento mais rápido (verifica a cada segundo)
        for _ in range(sleep_time):
            time.sleep(1)
            control.refresh_from_db() # Recarrega o estado do banco de dados.
            if not control.is_running:
                print(f"Comando de parada recebido para o bot do usuário {user.username}. Encerrando loop...")
                break
        
        # Garante que o estado seja recarregado caso o loop de sleep termine normalmente.
        control.refresh_from_db()

    # 6. Fim do loop (quando control.is_running se torna False).
    print(f"--- Loop do bot para {user.username} no símbolo {control.symbol} finalizado. ---")
    enviar_notificacao(
        f"🛑 [{bot_instance.symbol}] *Bot PARADO*\nMonitoramento encerrado pelo usuário.",
        user_profile.telegram_bot_token,
        user_profile.telegram_chat_id
    )
