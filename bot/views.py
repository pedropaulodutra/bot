import json
import pandas as pd
import numpy as np
from datetime import timedelta

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from binance.client import Client
from binance.exceptions import BinanceAPIException
from .models import BotControl, UserProfile, Trade
from .tasks import trading_bot_task

@login_required
def dashboard(request):
    control, created = BotControl.objects.get_or_create(user=request.user)
    user_profile = request.user.userprofile

    if request.method == 'POST':
        if 'save_settings' in request.POST:
            control.symbol = request.POST.get('symbol').upper()
            control.timeframe = request.POST.get('timeframe')
            control.ema_fast = int(request.POST.get('ema_fast'))
            control.ema_slow = int(request.POST.get('ema_slow'))
            control.quantidade_usdt = float(request.POST.get('quantidade_usdt'))
            control.leverage = int(request.POST.get('leverage'))
            control.save()
            messages.success(request, "Configurações salvas com sucesso!")
        
        elif 'toggle_bot' in request.POST:
            if not user_profile.api_key or not user_profile.api_secret:
                messages.error(request, "Você não pode iniciar o bot sem antes configurar suas chaves de API no painel de Admin.")
            else:
                if control.is_running:
                    control.is_running = False
                    messages.warning(request, "Bot parado! O loop em segundo plano terminará após a verificação atual.")
                else:
                    control.is_running = True
                    messages.success(request, f"Bot iniciado para {control.symbol}! A tarefa está rodando em segundo plano.")
                    trading_bot_task.delay(request.user.id)
                control.save()
        
        elif 'manual_trade' in request.POST:
            if not user_profile.api_key or not user_profile.api_secret:
                messages.error(request, "Suas chaves de API não estão configuradas no seu perfil. Impossível enviar ordem.")
            else:
                symbol = request.POST.get('symbol_manual').upper()
                side = request.POST.get('side_manual')
                quantity = request.POST.get('quantity_manual')
                leverage = request.POST.get('leverage_manual', '1')
                try:
                    client = Client(user_profile.api_key, user_profile.api_secret, testnet=False)
                    client.futures_change_leverage(symbol=symbol, leverage=leverage)
                    client.futures_create_order(
                        symbol=symbol, side=side, type=Client.ORDER_TYPE_MARKET, quantity=quantity
                    )
                    messages.success(request, f"Ordem manual de {side} para {quantity} {symbol} enviada!")
                except BinanceAPIException as e:
                    messages.error(request, f"Erro no trade manual: {e.message}")
                except Exception as e:
                    messages.error(request, f"Erro inesperado no trade manual: {e}")

        return redirect('dashboard')

    # --- DADOS PARA O TEMPLATE ---
    context_data = {
        'futures_balances': [],
        'positions': [],
        'error_message': None,
        'performance_data_json': '{}',
        'kpis': {'total_trades': 0, 'win_rate': 0, 'total_pnl': 0}
    }

    try:
        if user_profile.api_key and user_profile.api_secret:
            client = Client(user_profile.api_key, user_profile.api_secret, testnet=False)
            
            # --- Bloco 1: Análise de Performance (Buscando de TODOS os símbolos da conta) ---
            
            seven_days_ago_ms = int((timezone.now() - timedelta(days=7)).timestamp() * 1000)

            # Busca o histórico de trades da conta inteira, sem especificar símbolo
            trade_history = client.futures_account_trades(startTime=seven_days_ago_ms)

            # Filtra apenas os trades que tiveram um PnL realizado (fechamento de posição)
            closed_trades = [t for t in trade_history if float(t['realizedPnl']) != 0]

            if closed_trades:
                total_trades = len(closed_trades)
                pnls = [float(t['realizedPnl']) for t in closed_trades]
                wins = sum(1 for pnl in pnls if pnl > 0)
                total_pnl = sum(pnls)
                
                context_data['kpis']['total_trades'] = total_trades
                context_data['kpis']['win_rate'] = round((wins / total_trades) * 100, 2) if total_trades > 0 else 0
                context_data['kpis']['total_pnl'] = round(total_pnl, 2)
                
                # Preparando dados para os gráficos de performance
                perf_data = {
                    'pnl_por_trade_labels': [f"{t['symbol']}-{i+1}" for i, t in enumerate(closed_trades)],
                    'pnl_por_trade_data': [round(pnl, 2) for pnl in pnls],
                    'equity_curve_labels': [pd.to_datetime(t['time'], unit='ms').strftime('%d/%m %H:%M') for t in closed_trades],
                    'equity_curve_data': [round(pnl, 2) for pnl in np.cumsum(pnls)]
                }
                context_data['performance_data_json'] = json.dumps(perf_data)

            # --- Bloco 2: Busca de dados da Conta (Saldos e Posições Atuais) ---
            account_balances = client.futures_account_balance()
            context_data['futures_balances'] = [b for b in account_balances if float(b['balance']) > 0]
            account_info = client.futures_account()
            context_data['positions'] = [p for p in account_info['positions'] if float(p['positionAmt']) != 0]

        else:
            context_data['error_message'] = "Suas chaves de API não estão configuradas."

    except BinanceAPIException as e:
        context_data['error_message'] = f"Erro de API da Binance: {e.message}"
    except Exception as e:
        context_data['error_message'] = f"Ocorreu um erro inesperado: {e}"

    # --- CONTEXTO FINAL ENVIADO PARA O TEMPLATE ---
    context = {
        'control': control,
        'balances': context_data['futures_balances'],
        'positions': context_data['positions'],
        'error_message': context_data['error_message'],
        'performance_data_json': context_data['performance_data_json'],
        'kpis': context_data['kpis']
    }
    return render(request, 'bot/dashboard.html', context)