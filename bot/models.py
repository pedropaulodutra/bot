from django.db import models
from django.contrib.auth.models import User

# Modelo para guardar as informações extras do usuário
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    api_key = models.CharField(max_length=200, blank=True, null=True)
    api_secret = models.CharField(max_length=200, blank=True, null=True)
    telegram_bot_token = models.CharField(max_length=100, blank=True, null=True)
    telegram_chat_id = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.user.username
    
# Modelo para a configuração do bot de cada usuário
class BotControl(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_running = models.BooleanField(default=False)
    
    symbol = models.CharField(max_length=20, default="BTCUSDT")
    timeframe = models.CharField(max_length=10, default="15m")
    ema_fast = models.IntegerField(default=6)
    ema_slow = models.IntegerField(default=12)
    quantidade_usdt = models.FloatField(default=20.0)
    leverage = models.IntegerField(default=5)

    def __str__(self):
        return f"{self.user.username}'s Bot ({self.symbol}) - Running: {self.is_running}"
    

class Trade(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=20)
    side = models.CharField(max_length=5) # 'long' ou 'short'
    
    entry_price = models.FloatField()
    exit_price = models.FloatField(null=True, blank=True)
    quantity = models.FloatField()
    
    pnl = models.FloatField(null=True, blank=True) # Lucro/Prejuízo em USDT
    pnl_percent = models.FloatField(null=True, blank=True) # Lucro/Prejuízo em %

    entry_timestamp = models.DateTimeField(auto_now_add=True)
    exit_timestamp = models.DateTimeField(null=True, blank=True)
    
    is_open = models.BooleanField(default=True)

    def __str__(self):
        status = "OPEN" if self.is_open else "CLOSED"
        return f"{self.user.username} | {self.symbol} | {self.side.upper()} | {status}"