import time
import math
import numpy as np
import pandas as pd
import pandas_ta as ta

from binance.client import Client
from binance.exceptions import BinanceAPIException
from django.conf import settings
from django.utils import timezone

# Importa os modelos e a função de notificação
from .models import Trade
from .telegram import enviar_notificacao

# ===================================================================
# CLASSE 1: EmaAnalyzer (sem alterações)
# ===================================================================
class EmaAnalyzer:
    def __init__(self, prices):
        self.prices = np.array(prices)

    def calcular_ema(self, period):
        if len(self.prices) < period:
            return []
        df = pd.DataFrame(self.prices, columns=["close"])
        return ta.ema(df["close"], length=period).dropna().tolist()

# ===================================================================
# CLASSE 2: BinanceTrader (sem alterações)
# ===================================================================
class BinanceTrader:
    def __init__(self, api_key, api_secret):
        self.client = Client(api_key, api_secret, testnet=True)

    def market_order(self, symbol, side, quantity_str, reduceOnly=False):
        try:
            print(f"Enviando ordem: {symbol}, {side}, {quantity_str}, reduceOnly={reduceOnly}")
            ordem = self.client.futures_create_order(
                symbol=symbol, side=side, type='MARKET', quantity=quantity_str, reduceOnly=reduceOnly
            )
            print(f"Ordem {side} enviada com sucesso para {symbol}.")
            return ordem
        except BinanceAPIException as e:
            print(f"Erro de API da Binance: {e.message}")
            return None
        except Exception as e:
            print(f"Erro inesperado ao enviar ordem: {e}")
            return None

    def get_current_price(self, symbol):
        try:
            return float(self.client.futures_ticker(symbol=symbol)['lastPrice'])
        except Exception as e:
            print(f"Erro ao obter preço atual para {symbol}: {e}")
            return None
            
# ===================================================================
# CLASSE 3: TradingBot (com lógica para registrar trades)
# ===================================================================
class TradingBot:
    def __init__(self, control_params, user_profile):
        self.symbol = control_params.symbol.upper()
        self.quantidade_usdt = float(control_params.quantidade_usdt)
        self.leverage = control_params.leverage
        self.timeframe = control_params.timeframe
        self.ema_fast_period = control_params.ema_fast
        self.ema_slow_period = control_params.ema_slow
        self.user_profile = user_profile
        self.trader = BinanceTrader(user_profile.api_key, user_profile.api_secret)
        self.prices = []
        
        try:
            self.trader.client.futures_change_leverage(symbol=self.symbol, leverage=self.leverage)
            self.trader.client.futures_change_margin_type(symbol=self.symbol, marginType="CROSSED")
        except Exception as e:
            print(f"[{self.symbol}] Aviso ao configurar: {e}")

        self.estado = "IDLE"
        self.posicao_atual_tipo = None
        self.sinal_pendente_tipo = None
        self.preco_entrada = 0.0
        self.quantidade_em_moeda = 0.0
        self.MAX_DISTANCE_FROM_EMA_PERCENT = 3.0
        
        self.atualizar_estado_posicao()

    def carregar_precos_historicos(self):
        try:
            limit = max(200, self.ema_slow_period * 2)
            candles = self.trader.client.futures_klines(symbol=self.symbol, interval=self.timeframe, limit=limit)
            self.prices = [float(c[4]) for c in candles]
        except Exception as e:
            print(f"[{self.symbol}] Erro ao carregar históricos: {e}")

    def atualizar_estado_posicao(self):
        try:
            posicoes = self.trader.client.futures_position_information(symbol=self.symbol)
            posicao_encontrada = False
            for pos in posicoes:
                if pos["symbol"] == self.symbol and float(pos["positionAmt"]) != 0:
                    quantidade = float(pos["positionAmt"])
                    novo_tipo = "long" if quantidade > 0 else "short"
                    if self.estado == "IDLE":
                        self.estado = "IN_POSITION"
                    self.posicao_atual_tipo = novo_tipo
                    self.quantidade_em_moeda = abs(quantidade)
                    self.preco_entrada = float(pos["entryPrice"])
                    posicao_encontrada = True
                    break

            if not posicao_encontrada and self.estado == "IN_POSITION":
                self.estado = "IDLE"
                self.posicao_atual_tipo = None
                self.quantidade_em_moeda = 0.0
        except Exception as e:
            print(f"[{self.symbol}] Erro ao atualizar estado da posição: {e}")

    def obter_precisao_quantidade(self):
        try:
            info = self.trader.client.futures_exchange_info()
            for symbol_info in info["symbols"]:
                if symbol_info["symbol"] == self.symbol:
                    return int(symbol_info["quantityPrecision"])
            return 3
        except:
            return 3

    def fechar_posicao_atual(self, motivo):
        if not self.posicao_atual_tipo: return False
        
        side = "SELL" if self.posicao_atual_tipo == "long" else "BUY"
        precisao = self.obter_precisao_quantidade()
        qtd_str = f"{self.quantidade_em_moeda:.{precisao}f}"
        
        trade_aberto = Trade.objects.filter(user=self.user_profile.user, symbol=self.symbol, is_open=True).first()

        order_result = self.trader.market_order(self.symbol, side, qtd_str, reduceOnly=True)
        
        if order_result:
            enviar_notificacao(
                f"🚨 *Posição Fechada* 🚨\nSímbolo: `{self.symbol}`\nMotivo: {motivo}",
                token=self.user_profile.telegram_bot_token, chat_id=self.user_profile.telegram_chat_id
            )
            
            if trade_aberto:
                preco_saida = self.trader.get_current_price(self.symbol)
                if preco_saida:
                    pnl_usdt = (preco_saida - trade_aberto.entry_price) * trade_aberto.quantity
                    if self.posicao_atual_tipo == 'short': pnl_usdt = -pnl_usdt
                    
                    margem_inicial = (trade_aberto.entry_price * trade_aberto.quantity) / self.leverage
                    pnl_percent = (pnl_usdt / margem_inicial) * 100 if margem_inicial > 0 else 0

                    trade_aberto.exit_price = preco_saida
                    trade_aberto.exit_timestamp = timezone.now()
                    trade_aberto.pnl = pnl_usdt
                    trade_aberto.pnl_percent = pnl_percent
                    trade_aberto.is_open = False
                    trade_aberto.save()

            return True
        
        print("Falha ao fechar a posição.")
        return False
            
    def _is_price_near_ema(self, price, ema):
        if ema == 0: return False
        distance_percent = (abs(price - ema) / ema) * 100
        return distance_percent <= self.MAX_DISTANCE_FROM_EMA_PERCENT

    def _abrir_posicao(self, sinal_tipo, preco_atual):
        precisao = self.obter_precisao_quantidade()
        quantidade_moeda = (self.quantidade_usdt * self.leverage) / preco_atual
        qtd_str = f"{quantidade_moeda:.{precisao}f}"
        side = "BUY" if sinal_tipo == "long" else "SELL"
        
        order_result = self.trader.market_order(self.symbol, side, qtd_str)
        if order_result:
            enviar_notificacao(
                f"✅ *Posição Aberta*\nSímbolo: `{self.symbol}`\nTipo: *{sinal_tipo.upper()}*",
                token=self.user_profile.telegram_bot_token, chat_id=self.user_profile.telegram_chat_id
            )
            # Salva o novo trade no banco de dados
            Trade.objects.create(
                user=self.user_profile.user,
                symbol=self.symbol,
                side=sinal_tipo,
                entry_price=self.trader.get_current_price(self.symbol),
                quantity=float(qtd_str)
            )
            self.atualizar_estado_posicao()
            return True
        return False

    def run_single_check(self):
        print(f"\n--- [{self.symbol} | {self.timeframe}] Checando... Estado: {self.estado} ---")
        self.carregar_precos_historicos()
        if len(self.prices) < self.ema_slow_period: return

        preco_atual = self.prices[-1]
        analyzer = EmaAnalyzer(self.prices)
        ema_fast = analyzer.calcular_ema(self.ema_fast_period)
        ema_slow = analyzer.calcular_ema(self.ema_slow_period)
        if len(ema_fast) < 2 or len(ema_slow) < 2: return

        ema_fast_a, ema_fast_p = ema_fast[-1], ema_fast[-2]
        ema_slow_a, ema_slow_p = ema_slow[-1], ema_slow[-2]
        
        print(f"[{self.symbol}] Preço: {preco_atual:.4f} | EMA Rápida: {ema_fast_a:.4f} | EMA Lenta: {ema_slow_a:.4f}")

        if self.estado == "IDLE":
            cruzou_para_cima = ema_fast_p < ema_slow_p and ema_fast_a > ema_slow_a
            cruzou_para_baixo = ema_fast_p > ema_slow_p and ema_fast_a < ema_slow_a
            sinal_tipo = "long" if cruzou_para_cima else "short" if cruzou_para_baixo else None
            
            if sinal_tipo:
                if self._is_price_near_ema(preco_atual, ema_slow_a):
                    print(f"SINAL DE {sinal_tipo.upper()} e preço próximo da EMA. Abrindo posição.")
                    self._abrir_posicao(sinal_tipo, preco_atual)
                else:
                    print(f"Sinal de {sinal_tipo.upper()} detectado, mas preço distante. Aguardando pullback.")
                    self.estado = "AWAITING_PULLBACK"
                    self.sinal_pendente_tipo = sinal_tipo

        elif self.estado == "AWAITING_PULLBACK":
            sinal_ainda_valido = (self.sinal_pendente_tipo == "long" and ema_fast_a > ema_slow_a) or \
                                 (self.sinal_pendente_tipo == "short" and ema_fast_a < ema_slow_a)

            if not sinal_ainda_valido:
                print(f"Sinal de {self.sinal_pendente_tipo.upper()} invalidado. Cancelando espera.")
                self.estado = "IDLE"
                self.sinal_pendente_tipo = None
            elif self._is_price_near_ema(preco_atual, ema_slow_a):
                print(f"Pullback para {self.sinal_pendente_tipo.upper()} confirmado! Abrindo posição.")
                self._abrir_posicao(self.sinal_pendente_tipo, preco_atual)
                self.sinal_pendente_tipo = None

        elif self.estado == "IN_POSITION":
            reversao_long = self.posicao_atual_tipo == "long" and ema_fast_a < ema_slow_a
            reversao_short = self.posicao_atual_tipo == "short" and ema_fast_a > ema_slow_a
            
            if reversao_long:
                motivo = f"Reversão Long->Short"
                if self.fechar_posicao_atual(motivo):
                    time.sleep(2)
                    self._abrir_posicao("short", preco_atual)

            elif reversao_short:
                motivo = f"Reversão Short->Long"
                if self.fechar_posicao_atual(motivo):
                    time.sleep(2)
                    self._abrir_posicao("long", preco_atual)