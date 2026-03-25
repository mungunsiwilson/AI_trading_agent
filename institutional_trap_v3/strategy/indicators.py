import numpy as np
import pandas as pd

def calculate_vwma(df, period=50):
    """Volume Weighted Moving Average"""
    if 'volume' not in df.columns: return None
    pv = df['close'] * df['volume']
    vwma = pv.rolling(window=period).sum() / df['volume'].rolling(window=period).sum()
    return vwma.iloc[-1]

def calculate_atr(df, period=10):
    """Average True Range"""
    high = df['high']
    low = df['low']
    close = df['close'].shift(1)
    
    tr1 = high - low
    tr2 = abs(high - close)
    tr3 = abs(low - close)
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr.iloc[-1]

def calculate_delta(df):
    """
    Approximate Delta using Close vs Open and Volume.
    True Delta requires tick data, but for M1 bars:
    Delta ≈ (Close - Open) / (High - Low) * Volume
    """
    if len(df) < 2: return 0
    
    last = df.iloc[-1]
    range_val = last['high'] - last['low']
    if range_val == 0: return 0
    
    direction = (last['close'] - last['open']) / range_val
    delta = direction * last['volume']
    return delta