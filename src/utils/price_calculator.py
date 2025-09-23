import asyncio
import aiohttp
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from ..core.web3_client import Web3Client
from ..core.logger import logger

class PriceCalculator:
    """Advanced price calculator with multiple DEX support and price aggregation."""
    
    def __init__(self, web3_client: Web3Client):
        self.web3_client = web3_client
        
        # Price cache to avoid excessive API calls
        self.price_cache: Dict[str, Tuple[float, datetime]] = {}
        self.cache_duration = timedelta(seconds=30)  # Cache prices for 30 seconds
        
        # DEX router addresses and ABIs
        self.dex_routers = {
            'uniswap_v3': '0x2626664c2603336E57B271c5C0b26F421741e481',
            'baseswap': '0x327Df1E6de05895d2ab08513aaDD9313Fe505d86',
            'camelot': '0xc873fEcbd354f5A56E00E710B90EF4201db2448d'
        }
        
        # Common token addresses on Base
        self.common_tokens = {
            'WETH': '0x4200000000000000000000000000000000000006',
            'USDC': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
            'DAI': '0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb'
        }
        
        logger.info("PriceCalculator initialized")
    
    async def get_eth_price_usd(self) -> Optional[float]:
        """Get current ETH price in USD."""
        try:
            cache_key = "ETH_USD"
            
            # Check cache
            if cache_key in self.price_cache:
                price, timestamp = self.price_cache[cache_key]
                if datetime.now() - timestamp < self.cache_duration:
                    return price
            
            # Fetch from multiple sources and average
            prices = []
            
            # CoinGecko API
            try:
                async with aiohttp.ClientSession() as session:
                    url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
                    async with session.get(url, timeout=5) as response:
                        if response.status == 200:
                            data = await response.json()
                            eth_price = data.get('ethereum', {}).get('usd')
                            if eth_price:
                                prices.append(eth_price)
            except Exception as e:
                logger.debug("Error fetching ETH price from CoinGecko", error=str(e))
            
            # CoinMarketCap API (if available)
            try:
                async with aiohttp.ClientSession() as session:
                    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol=ETH"
                    headers = {'X-CMC_PRO_API_KEY': 'your_api_key_here'}  # Would need real API key
                    async with session.get(url, headers=headers, timeout=5) as response:
                        if response.status == 200:
                            data = await response.json()
                            eth_price = data.get('data', {}).get('ETH', {}).get('quote', {}).get('USD', {}).get('price')
                            if eth_price:
                                prices.append(eth_price)
            except Exception as e:
                logger.debug("Error fetching ETH price from CoinMarketCap", error=str(e))
            
            if prices:
                # Average the prices
                avg_price = sum(prices) / len(prices)
                
                # Cache the result
                self.price_cache[cache_key] = (avg_price, datetime.now())
                
                logger.debug("ETH price updated", price=avg_price, sources=len(prices))
                return avg_price
            
            # Fallback to a default price if APIs fail
            logger.warning("Could not fetch ETH price, using fallback")
            return 2000.0  # Fallback price
            
        except Exception as e:
            logger.error("Error getting ETH price", error=str(e))
            return None
    
    async def get_token_price_eth(self, token_address: str) -> Optional[float]:
        """Get token price in ETH from DEXs."""
        try:
            cache_key = f"{token_address}_ETH"
            
            # Check cache
            if cache_key in self.price_cache:
                price, timestamp = self.price_cache[cache_key]
                if datetime.now() - timestamp < self.cache_duration:
                    return price
            
            # Get prices from multiple DEXs
            prices = []
            
            # Try each DEX
            for dex_name, router_address in self.dex_routers.items():
                try:
                    price = await self._get_price_from_dex(token_address, self.common_tokens['WETH'], router_address)
                    if price and price > 0:
                        prices.append(price)
                        logger.debug("Got price from DEX", dex=dex_name, price=price)
                except Exception as e:
                    logger.debug(f"Error getting price from {dex_name}", error=str(e))
            
            if prices:
                # Use median price to avoid outliers
                prices.sort()
                median_price = prices[len(prices) // 2]
                
                # Cache the result
                self.price_cache[cache_key] = (median_price, datetime.now())
                
                logger.debug("Token price in ETH", token_address=token_address, price=median_price)
                return median_price
            
            logger.warning("Could not get token price in ETH", token_address=token_address)
            return None
            
        except Exception as e:
            logger.error("Error getting token price in ETH", token_address=token_address, error=str(e))
            return None
    
    async def get_token_price_usd(self, token_address: str) -> Optional[float]:
        """Get token price in USD."""
        try:
            # First get price in ETH
            price_eth = await self.get_token_price_eth(token_address)
            if not price_eth:
                return None
            
            # Then get ETH price in USD
            eth_price_usd = await self.get_eth_price_usd()
            if not eth_price_usd:
                return None
            
            # Calculate USD price
            price_usd = price_eth * eth_price_usd
            
            logger.debug("Token price in USD", 
                        token_address=token_address, 
                        price_eth=price_eth,
                        eth_price_usd=eth_price_usd,
                        price_usd=price_usd)
            
            return price_usd
            
        except Exception as e:
            logger.error("Error getting token price in USD", token_address=token_address, error=str(e))
            return None
    
    async def _get_price_from_dex(self, token_in: str, token_out: str, router_address: str) -> Optional[float]:
        """Get price from a specific DEX router."""
        try:
            # This would implement the actual DEX price fetching logic
            # For Uniswap V3, this would involve:
            # 1. Finding the pool address
            # 2. Getting the current tick/price from the pool
            # 3. Converting to human-readable price
            
            # For now, return a placeholder calculation
            # In real implementation, this would call the DEX contracts
            
            # Simplified router ABI for getAmountsOut
            router_abi = [
                {
                    "inputs": [
                        {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                        {"internalType": "address[]", "name": "path", "type": "address[]"}
                    ],
                    "name": "getAmountsOut",
                    "outputs": [
                        {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}
                    ],
                    "stateMutability": "view",
                    "type": "function"
                }
            ]
            
            try:
                contract = self.web3_client.w3.eth.contract(
                    address=router_address,
                    abi=router_abi
                )
                
                # Get price for 1 token (adjusted for decimals)
                amount_in = 10**18  # 1 token with 18 decimals
                path = [token_in, token_out]
                
                amounts_out = contract.functions.getAmountsOut(amount_in, path).call()
                
                if len(amounts_out) >= 2:
                    amount_out = amounts_out[-1]
                    price = amount_out / amount_in
                    return price
                
            except Exception as e:
                logger.debug("Error calling DEX contract", router=router_address, error=str(e))
            
            return None
            
        except Exception as e:
            logger.debug("Error getting price from DEX", router=router_address, error=str(e))
            return None
    
    async def get_best_price_route(self, token_in: str, token_out: str, amount_in: float) -> Optional[Dict[str, any]]:
        """Find the best price route across all DEXs."""
        try:
            routes = []
            
            # Check all DEXs
            for dex_name, router_address in self.dex_routers.items():
                try:
                    price = await self._get_price_from_dex(token_in, token_out, router_address)
                    if price and price > 0:
                        amount_out = amount_in * price
                        routes.append({
                            'dex': dex_name,
                            'router': router_address,
                            'price': price,
                            'amount_out': amount_out,
                            'slippage_estimate': 0.01  # 1% estimated slippage
                        })
                except Exception as e:
                    logger.debug(f"Error checking {dex_name} for best route", error=str(e))
            
            if not routes:
                return None
            
            # Sort by amount out (best price)
            routes.sort(key=lambda x: x['amount_out'], reverse=True)
            best_route = routes[0]
            
            logger.info("Best price route found", 
                       dex=best_route['dex'],
                       price=best_route['price'],
                       amount_out=best_route['amount_out'])
            
            return best_route
            
        except Exception as e:
            logger.error("Error finding best price route", error=str(e))
            return None
    
    async def calculate_slippage_impact(self, token_address: str, amount_eth: float) -> float:
        """Calculate estimated slippage impact for a trade."""
        try:
            # This would analyze liquidity depth and estimate slippage
            # For now, return a simple estimate based on trade size
            
            # Get token liquidity (simplified)
            token_info = await self.web3_client.get_token_info(token_address)
            if not token_info:
                return 0.05  # 5% default slippage
            
            liquidity_eth = token_info.liquidity_eth
            
            # Calculate slippage based on trade size vs liquidity
            if liquidity_eth > 0:
                trade_impact = amount_eth / liquidity_eth
                
                # Estimate slippage (simplified model)
                if trade_impact < 0.01:  # < 1% of liquidity
                    slippage = 0.005  # 0.5%
                elif trade_impact < 0.05:  # < 5% of liquidity
                    slippage = 0.02   # 2%
                elif trade_impact < 0.1:   # < 10% of liquidity
                    slippage = 0.05   # 5%
                else:
                    slippage = 0.1    # 10%
                
                return slippage
            
            return 0.05  # Default 5% slippage
            
        except Exception as e:
            logger.error("Error calculating slippage impact", error=str(e))
            return 0.05
    
    def clear_cache(self):
        """Clear the price cache."""
        self.price_cache.clear()
        logger.info("Price cache cleared")
    
    def get_cache_stats(self) -> Dict[str, any]:
        """Get cache statistics."""
        return {
            "cached_prices": len(self.price_cache),
            "cache_duration_seconds": self.cache_duration.total_seconds()
        }