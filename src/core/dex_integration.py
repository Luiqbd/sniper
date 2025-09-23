import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from web3 import Web3
from ..core.config import Config
from ..core.web3_client import Web3Client
from ..core.logger import logger

@dataclass
class SwapRoute:
    dex_name: str
    router_address: str
    path: List[str]
    amount_out: float
    gas_estimate: int
    slippage_impact: float

@dataclass
class SwapResult:
    success: bool
    tx_hash: Optional[str]
    amount_out: Optional[float]
    gas_used: Optional[int]
    error_message: Optional[str] = None

class DEXIntegration:
    """Advanced DEX integration with multi-DEX routing and optimal execution."""
    
    def __init__(self, config: Config, web3_client: Web3Client):
        self.config = config
        self.web3_client = web3_client
        
        # DEX configurations
        self.dex_configs = {
            'uniswap_v3': {
                'router': config.dex.uniswap_v3_router,
                'factory': '0x33128a8fC17869897dcE68Ed026d694621f6FDfD',
                'quoter': '0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a',
                'fee_tiers': [100, 500, 3000, 10000]  # 0.01%, 0.05%, 0.3%, 1%
            },
            'baseswap': {
                'router': config.dex.baseswap_router,
                'factory': '0xFDa619b6d20975be80A10332cD39b9a4b0FAa8BB',
                'fee': 3000  # 0.3%
            },
            'camelot': {
                'router': config.dex.camelot_router,
                'factory': '0x6EcCab422D763aC031210895C81787E87B91425',
                'fee': 3000  # 0.3%
            }
        }
        
        # Router ABIs (simplified)
        self.router_abi = [
            {
                "inputs": [
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                    {"internalType": "address[]", "name": "path", "type": "address[]"},
                    {"internalType": "address", "name": "to", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"}
                ],
                "name": "swapExactTokensForTokens",
                "outputs": [
                    {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}
                ],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                    {"internalType": "address[]", "name": "path", "type": "address[]"},
                    {"internalType": "address", "name": "to", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"}
                ],
                "name": "swapExactETHForTokens",
                "outputs": [
                    {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}
                ],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                    {"internalType": "address[]", "name": "path", "type": "address[]"},
                    {"internalType": "address", "name": "to", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"}
                ],
                "name": "swapExactTokensForETH",
                "outputs": [
                    {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}
                ],
                "stateMutability": "nonpayable",
                "type": "function"
            },
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
        
        logger.info("DEXIntegration initialized", supported_dexs=len(self.dex_configs))
    
    async def get_best_swap_route(self, token_in: str, token_out: str, amount_in: float) -> Optional[SwapRoute]:
        """Find the best swap route across all DEXs."""
        try:
            routes = []
            
            # Check each DEX for the best route
            for dex_name, dex_config in self.dex_configs.items():
                try:
                    route = await self._get_dex_route(dex_name, token_in, token_out, amount_in)
                    if route:
                        routes.append(route)
                except Exception as e:
                    logger.debug(f"Error getting route from {dex_name}", error=str(e))
            
            if not routes:
                logger.warning("No valid routes found", token_in=token_in, token_out=token_out)
                return None
            
            # Sort by amount out (best price)
            routes.sort(key=lambda x: x.amount_out, reverse=True)
            best_route = routes[0]
            
            logger.info("Best swap route found", 
                       dex=best_route.dex_name,
                       amount_out=best_route.amount_out,
                       slippage=best_route.slippage_impact)
            
            return best_route
            
        except Exception as e:
            logger.error("Error finding best swap route", error=str(e))
            return None
    
    async def _get_dex_route(self, dex_name: str, token_in: str, token_out: str, amount_in: float) -> Optional[SwapRoute]:
        """Get swap route from a specific DEX."""
        try:
            dex_config = self.dex_configs[dex_name]
            router_address = dex_config['router']
            
            # Create router contract
            router_contract = self.web3_client.w3.eth.contract(
                address=router_address,
                abi=self.router_abi
            )
            
            # Convert amount to wei
            amount_in_wei = int(amount_in * 10**18)  # Assuming 18 decimals
            
            # Define swap path
            path = [token_in, token_out]
            
            # Get amounts out
            try:
                amounts_out = router_contract.functions.getAmountsOut(amount_in_wei, path).call()
                amount_out_wei = amounts_out[-1]
                amount_out = amount_out_wei / 10**18  # Convert back to human readable
                
                # Estimate gas
                gas_estimate = await self._estimate_swap_gas(router_contract, amount_in_wei, path)
                
                # Calculate slippage impact (simplified)
                slippage_impact = await self._calculate_slippage_impact(dex_name, token_in, token_out, amount_in)
                
                return SwapRoute(
                    dex_name=dex_name,
                    router_address=router_address,
                    path=path,
                    amount_out=amount_out,
                    gas_estimate=gas_estimate,
                    slippage_impact=slippage_impact
                )
                
            except Exception as e:
                logger.debug(f"Error getting amounts from {dex_name}", error=str(e))
                return None
            
        except Exception as e:
            logger.error(f"Error getting route from {dex_name}", error=str(e))
            return None
    
    async def _estimate_swap_gas(self, router_contract, amount_in_wei: int, path: List[str]) -> int:
        """Estimate gas for swap transaction."""
        try:
            # This would estimate gas for the actual swap
            # For now, return a reasonable estimate
            return self.config.gas.gas_limit_swap
            
        except Exception as e:
            logger.debug("Error estimating gas", error=str(e))
            return self.config.gas.gas_limit_swap
    
    async def _calculate_slippage_impact(self, dex_name: str, token_in: str, token_out: str, amount_in: float) -> float:
        """Calculate slippage impact for the trade."""
        try:
            # This would analyze liquidity depth and calculate actual slippage
            # For now, return a simple estimate
            
            if amount_in < 0.1:  # Small trade
                return 0.005  # 0.5%
            elif amount_in < 1.0:  # Medium trade
                return 0.02   # 2%
            else:  # Large trade
                return 0.05   # 5%
                
        except Exception as e:
            logger.debug("Error calculating slippage", error=str(e))
            return 0.05
    
    async def execute_swap(self, route: SwapRoute, amount_in: float, min_amount_out: float) -> SwapResult:
        """Execute a swap using the specified route."""
        try:
            logger.info("Executing swap", 
                       dex=route.dex_name,
                       amount_in=amount_in,
                       min_amount_out=min_amount_out)
            
            if self.config.dry_run_mode:
                logger.info("DRY RUN: Would execute swap", 
                           dex=route.dex_name,
                           amount_in=amount_in,
                           expected_out=route.amount_out)
                
                return SwapResult(
                    success=True,
                    tx_hash="0x" + "0" * 64,  # Fake hash
                    amount_out=route.amount_out,
                    gas_used=route.gas_estimate
                )
            
            # Create router contract
            router_contract = self.web3_client.w3.eth.contract(
                address=route.router_address,
                abi=self.router_abi
            )
            
            # Convert amounts to wei
            amount_in_wei = int(amount_in * 10**18)
            min_amount_out_wei = int(min_amount_out * 10**18)
            
            # Set deadline (10 minutes from now)
            deadline = int(self.web3_client.w3.eth.get_block('latest')['timestamp']) + 600
            
            # Determine swap function based on tokens
            weth_address = "0x4200000000000000000000000000000000000006"  # WETH on Base
            
            if route.path[0] == weth_address:
                # ETH to Token swap
                swap_function = router_contract.functions.swapExactETHForTokens(
                    min_amount_out_wei,
                    route.path,
                    self.web3_client.wallet_address,
                    deadline
                )
                
                # Build transaction
                transaction = self.web3_client.build_transaction(
                    to_address=route.router_address,
                    data=swap_function._encode_transaction_data(),
                    value=amount_in_wei
                )
                
            elif route.path[-1] == weth_address:
                # Token to ETH swap
                swap_function = router_contract.functions.swapExactTokensForETH(
                    amount_in_wei,
                    min_amount_out_wei,
                    route.path,
                    self.web3_client.wallet_address,
                    deadline
                )
                
                # Build transaction
                transaction = self.web3_client.build_transaction(
                    to_address=route.router_address,
                    data=swap_function._encode_transaction_data()
                )
                
            else:
                # Token to Token swap
                swap_function = router_contract.functions.swapExactTokensForTokens(
                    amount_in_wei,
                    min_amount_out_wei,
                    route.path,
                    self.web3_client.wallet_address,
                    deadline
                )
                
                # Build transaction
                transaction = self.web3_client.build_transaction(
                    to_address=route.router_address,
                    data=swap_function._encode_transaction_data()
                )
            
            # Execute transaction
            tx_hash = self.web3_client.sign_and_send_transaction(transaction)
            
            # Wait for confirmation
            receipt = self.web3_client.wait_for_transaction_receipt(tx_hash)
            
            if receipt['status'] == 1:
                logger.info("Swap executed successfully", 
                           tx_hash=tx_hash,
                           gas_used=receipt['gasUsed'])
                
                return SwapResult(
                    success=True,
                    tx_hash=tx_hash,
                    amount_out=route.amount_out,  # Would parse from logs in real implementation
                    gas_used=receipt['gasUsed']
                )
            else:
                logger.error("Swap transaction failed", tx_hash=tx_hash)
                return SwapResult(
                    success=False,
                    tx_hash=tx_hash,
                    amount_out=None,
                    gas_used=receipt['gasUsed'],
                    error_message="Transaction failed"
                )
            
        except Exception as e:
            logger.error("Error executing swap", error=str(e))
            return SwapResult(
                success=False,
                tx_hash=None,
                amount_out=None,
                gas_used=None,
                error_message=str(e)
            )
    
    async def buy_token_with_eth(self, token_address: str, eth_amount: float, min_tokens: float) -> SwapResult:
        """Buy tokens with ETH using the best available route."""
        try:
            weth_address = "0x4200000000000000000000000000000000000006"  # WETH on Base
            
            # Find best route
            route = await self.get_best_swap_route(weth_address, token_address, eth_amount)
            
            if not route:
                return SwapResult(
                    success=False,
                    tx_hash=None,
                    amount_out=None,
                    gas_used=None,
                    error_message="No valid route found"
                )
            
            # Execute swap
            return await self.execute_swap(route, eth_amount, min_tokens)
            
        except Exception as e:
            logger.error("Error buying token with ETH", token_address=token_address, error=str(e))
            return SwapResult(
                success=False,
                tx_hash=None,
                amount_out=None,
                gas_used=None,
                error_message=str(e)
            )
    
    async def sell_token_for_eth(self, token_address: str, token_amount: float, min_eth: float) -> SwapResult:
        """Sell tokens for ETH using the best available route."""
        try:
            weth_address = "0x4200000000000000000000000000000000000006"  # WETH on Base
            
            # Find best route
            route = await self.get_best_swap_route(token_address, weth_address, token_amount)
            
            if not route:
                return SwapResult(
                    success=False,
                    tx_hash=None,
                    amount_out=None,
                    gas_used=None,
                    error_message="No valid route found"
                )
            
            # Execute swap
            return await self.execute_swap(route, token_amount, min_eth)
            
        except Exception as e:
            logger.error("Error selling token for ETH", token_address=token_address, error=str(e))
            return SwapResult(
                success=False,
                tx_hash=None,
                amount_out=None,
                gas_used=None,
                error_message=str(e)
            )
    
    async def approve_token(self, token_address: str, spender_address: str, amount: float) -> bool:
        """Approve token spending for a DEX router."""
        try:
            logger.info("Approving token", token_address=token_address, spender=spender_address)
            
            if self.config.dry_run_mode:
                logger.info("DRY RUN: Would approve token", token_address=token_address)
                return True
            
            # ERC20 approve function ABI
            approve_abi = [{
                "inputs": [
                    {"internalType": "address", "name": "spender", "type": "address"},
                    {"internalType": "uint256", "name": "amount", "type": "uint256"}
                ],
                "name": "approve",
                "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
                "stateMutability": "nonpayable",
                "type": "function"
            }]
            
            # Create token contract
            token_contract = self.web3_client.w3.eth.contract(
                address=token_address,
                abi=approve_abi
            )
            
            # Convert amount to wei (max approval for convenience)
            amount_wei = 2**256 - 1  # Max uint256
            
            # Build approve transaction
            approve_function = token_contract.functions.approve(spender_address, amount_wei)
            
            transaction = self.web3_client.build_transaction(
                to_address=token_address,
                data=approve_function._encode_transaction_data()
            )
            
            # Execute transaction
            tx_hash = self.web3_client.sign_and_send_transaction(transaction)
            
            # Wait for confirmation
            receipt = self.web3_client.wait_for_transaction_receipt(tx_hash)
            
            success = receipt['status'] == 1
            
            if success:
                logger.info("Token approval successful", tx_hash=tx_hash)
            else:
                logger.error("Token approval failed", tx_hash=tx_hash)
            
            return success
            
        except Exception as e:
            logger.error("Error approving token", token_address=token_address, error=str(e))
            return False
    
    def get_supported_dexs(self) -> List[str]:
        """Get list of supported DEXs."""
        return list(self.dex_configs.keys())
    
    def get_dex_info(self, dex_name: str) -> Optional[Dict[str, str]]:
        """Get information about a specific DEX."""
        return self.dex_configs.get(dex_name)