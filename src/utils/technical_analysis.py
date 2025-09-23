import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from ..core.logger import logger

class TechnicalAnalyzer:
    """Technical analysis utilities for trading signals."""
    
    def __init__(self):
        logger.info("TechnicalAnalyzer initialized")
    
    def calculate_indicators(self, prices: pd.Series) -> Dict[str, float]:
        """Calculate various technical indicators."""
        try:
            indicators = {}
            
            # RSI (Relative Strength Index)
            indicators['rsi'] = self._calculate_rsi(prices)
            
            # MACD
            macd_line, signal_line = self._calculate_macd(prices)
            indicators['macd'] = macd_line
            indicators['macd_signal'] = 1 if macd_line > signal_line else -1
            
            # Moving Averages
            sma_20 = prices.rolling(window=20).mean().iloc[-1]
            sma_50 = prices.rolling(window=50).mean().iloc[-1]
            current_price = prices.iloc[-1]
            
            indicators['sma_20'] = sma_20
            indicators['sma_50'] = sma_50
            indicators['ma_signal'] = 1 if current_price > sma_20 else -1
            
            # Bollinger Bands
            bb_upper, bb_lower = self._calculate_bollinger_bands(prices)
            indicators['bb_upper'] = bb_upper
            indicators['bb_lower'] = bb_lower
            
            if current_price <= bb_lower:
                indicators['bb_signal'] = 1  # Buy signal
            elif current_price >= bb_upper:
                indicators['bb_signal'] = -1  # Sell signal
            else:
                indicators['bb_signal'] = 0
            
            # Volume signal (placeholder)
            indicators['volume_signal'] = 0
            
            return indicators
            
        except Exception as e:
            logger.error("Error calculating technical indicators", error=str(e))
            return {}
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI indicator."""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0
            
        except Exception as e:
            logger.error("Error calculating RSI", error=str(e))
            return 50.0
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """Calculate MACD indicator."""
        try:
            ema_fast = prices.ewm(span=fast).mean()
            ema_slow = prices.ewm(span=slow).mean()
            
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal).mean()
            
            return macd_line.iloc[-1], signal_line.iloc[-1]
            
        except Exception as e:
            logger.error("Error calculating MACD", error=str(e))
            return 0.0, 0.0
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> tuple:
        """Calculate Bollinger Bands."""
        try:
            sma = prices.rolling(window=period).mean()
            std = prices.rolling(window=period).std()
            
            upper_band = sma + (std * std_dev)
            lower_band = sma - (std * std_dev)
            
            return upper_band.iloc[-1], lower_band.iloc[-1]
            
        except Exception as e:
            logger.error("Error calculating Bollinger Bands", error=str(e))
            return 0.0, 0.0