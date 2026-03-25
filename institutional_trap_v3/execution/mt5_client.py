import MetaTrader5 as mt5
from config import Config
from utils.logger import get_logger
ACTION_SLTP = 5 

logger = get_logger("MT5Client")

class MT5Client:
    def __init__(self):
        self.mt5 = mt5
        self.connected = False

    def connect(self):
        if not self.mt5.initialize():
            logger.error(f"Init failed: {self.mt5.last_error()}")
            return False
            
        if Config.MT5_LOGIN:
            if not self.mt5.login(login=int(Config.MT5_LOGIN), password=Config.MT5_PASSWORD, server=Config.MT5_SERVER):
                logger.error(f"Login failed: {self.mt5.last_error()}")
                return False
        
        if not self.mt5.symbol_select(Config.SYMBOL):
            logger.error(f"Symbol select failed")
            return False
            
        self.connected = True
        logger.info(f"Connected: {Config.SYMBOL}")
        return True

    def get_rates(self, symbol, timeframe, count):
        rates = self.mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        return rates

    def get_tick(self, symbol):
        return self.mt5.symbol_info_tick(symbol)

    def get_position(self, symbol):
        positions = self.mt5.positions_get(symbol=symbol)
        return positions[0] if positions else None

    def build_order(self, symbol, type, volume, sl, tp):
        tick = self.get_tick(symbol)
        if not tick:
            logger.error("No tick data available for order building.")
            return None
        price = tick.ask if type == mt5.ORDER_TYPE_BUY else tick.bid
        tp = 0.0
        return {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 234000,
            "comment": "SMC_3TF",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }

    def execute_order(self, request):
        """Sends order to MT5"""
        if not request:
            return None
        
        # Send the order
        result = mt5.order_send(request)
        
        # Debug: Print raw result if it looks weird
        if result is None or isinstance(result, tuple):
            print(f"MT5 Order Send Raw Result: {result}")
            
        return result
    
    def build_modify_order(self, ticket, sl, tp=0.0):
        """Builds a request to modify Stop Loss and Take Profit"""
        action_code = getattr(mt5, "TRADE_ACTION_SLTP", 5)
        tick = self.get_tick(Config.SYMBOL)
        if not tick:
            return None
            
        # For modify orders, price field is often ignored but required by struct
        # We use the current market price
        current_price = tick.ask # Default, doesn't strictly matter for SL/TP mod
        tp = 0.0 # No TP modification in this case
        return {
            "action": action_code,
            "symbol": Config.SYMBOL,
            "position": ticket,
            "sl": sl,
            "tp": tp,
            "comment": "Trailing Stop Update",
        }

    def shutdown(self):
        self.mt5.shutdown()