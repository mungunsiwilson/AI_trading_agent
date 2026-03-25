from config import Config
from datetime import datetime
from utils.logger import get_logger

logger = get_logger("PosManager")
class PositionManager:
    def __init__(self):
        self.active_position = None
        self.last_exit_time = None
        self.close_reason = ""

    def init_position(self, direction, entry_price, sl, risk_step, entry_time):
        self.active_position = {
            'direction': direction,
            'entry_price': entry_price,
            'virtual_entry': entry_price,
            'current_sl': sl,
            'risk_step': risk_step,
            'entry_time': entry_time,
            'last_trail_active': False
        }
        logger.info(f"Pos Init: Dir={direction}, Entry={entry_price}, SL={sl}, StepSize={risk_step}")

    def clear_position(self):
        self.active_position = None
        self.close_reason = ""

    def set_last_exit(self):
        self.last_exit_time = datetime.now()

    def cooldown_active(self):
        if not self.last_exit_time: 
            return False
        return (datetime.now() - self.last_exit_time).total_seconds() < 60

    def update(self, position, tick, symbol):
        if not self.active_position: return None
        
        state = self.active_position
        direction = state['direction']
        current_price = tick.bid if direction == 'SHORT' else tick.ask
        
        # 1. Check Hard Stop Loss Hit (Server side might have caught it, but we check locally)
        if direction == 'LONG':
            if current_price <= state['current_sl']:
                self.close_reason = "Stop Loss Hit"
                return 'CLOSE'
        else: # SHORT
            if current_price >= state['current_sl']:
                self.close_reason = "Stop Loss Hit"
                return 'CLOSE'

        # 2. Calculate Trailing Logic (Step-Trail)
        # We compare Current Price vs Virtual Entry
        # If distance >= Initial Risk Step, we move SL to Virtual Entry, and move Virtual Entry to Current
        
        risk_step = state['risk_step']
        triggered = False
        
        if direction == 'LONG':
            profit_distance = current_price - state['virtual_entry']
            
            # Check if price moved enough to trigger a step
            if profit_distance >= risk_step:
                # New SL becomes the old Virtual Entry (which was the previous high water mark effectively)
                new_sl = state['virtual_entry']
                
                # Only update if the new SL is strictly higher than current SL (to avoid redundant updates)
                if new_sl > state['current_sl']:
                    state['current_sl'] = new_sl
                    # Move Virtual Entry up to Current Price to reset the counter for next step
                    state['virtual_entry'] = current_price
                    state['last_trail_price'] = current_price
                    triggered = True
                    logger.info(f"Trail Up: New SL={new_sl:.5f}, New Virtual Entry={current_price:.5f}")

        elif direction == 'SHORT':
            profit_distance = state['virtual_entry'] - current_price
            
            if profit_distance >= risk_step:
                new_sl = state['virtual_entry']
                
                # For shorts, new SL must be lower
                if new_sl < state['current_sl']:
                    state['current_sl'] = new_sl
                    state['virtual_entry'] = current_price
                    state['last_trail_price'] = current_price
                    triggered = True
                    logger.info(f"Trail Down: New SL={new_sl:.5f}, New Virtual Entry={current_price:.5f}")

        # Note: We do NOT return 'CLOSE' here. We just return None.
        # The main loop detects that 'active_position' state changed (SL updated) 
        # and sends a MODIFY order to MT5.
        
        return None