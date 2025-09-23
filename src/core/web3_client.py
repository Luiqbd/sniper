import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.exceptions import TransactionNotFound, BlockNotFound
import websockets
import aiohttp
from dataclasses import dataclass
from .config import Config
from .logger import logger

@dataclass
class TokenInfo:
    address: str
    name: str
    symbol: str
    decimals: int
    total_supply: int
    holders_count: int
    liquidity_eth: float

@dataclass
class Transaction:
    hash: str
    from_address: str
    to_address: str
    value: int
    gas_price: int
    gas_limit: int
    input_data: str
    block_number: Optional[int] = None

class Web3Client:
    """Enhanced Web3 client for Base network with mempool monitoring."""
    
    def __init__(self, config: Config):
        self.config = config
        self.w3 = Web3(Web3.HTTPProvider(config.network.rpc_url))
        
        # Add PoA middleware for Base network
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        # Setup account
        self.account = self.w3.eth.account.from_key(config.private_key)
        self.wallet_address = self.account.address
        
        # WebSocket connection for mempool monitoring
        self.ws_url = config.network.websocket_url
        self.ws_connection = None
        self.pending_txs = {}
        
        logger.info("Web3Client initialized", 
                   wallet_address=self.wallet_address,
                   network=config.network.rpc_url)
    
    async def connect_websocket(self):
        """Connect to WebSocket for real-time mempool monitoring."""
        try:
            self.ws_connection = await websockets.connect(self.ws_url)
            
            # Subscribe to pending transactions
            subscription = {
                "id": 1,
                "method": "eth_subscribe",
                "params": ["newPendingTransactions"]
            }
            
            await self.ws_connection.send(json.dumps(subscription))
            response = await self.ws_connection.recv()
            logger.info("WebSocket connected for mempool monitoring", response=response)
            
        except Exception as e:
            logger.error("Failed to connect WebSocket", error=str(e))
            raise
    
    async def monitor_mempool(self, callback):
        """Monitor mempool for new transactions."""
        if not self.ws_connection:
            await self.connect_websocket()
        
        try:
            async for message in self.ws_connection:
                data = json.loads(message)
                
                if 'params' in data and 'result' in data['params']:
                    tx_hash = data['params']['result']
                    
                    # Get transaction details
                    try:
                        tx = await self.get_transaction(tx_hash)
                        if tx:
                            await callback(tx)
                    except Exception as e:
                        logger.debug("Error processing mempool transaction", 
                                   tx_hash=tx_hash, error=str(e))
                        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed, attempting to reconnect")
            await self.connect_websocket()
            await self.monitor_mempool(callback)
        except Exception as e:
            logger.error("Error monitoring mempool", error=str(e))
            raise
    
    async def get_transaction(self, tx_hash: str) -> Optional[Transaction]:
        """Get transaction details by hash."""
        try:
            tx = self.w3.eth.get_transaction(tx_hash)
            
            return Transaction(
                hash=tx_hash,
                from_address=tx['from'],
                to_address=tx['to'] if tx['to'] else '',
                value=tx['value'],
                gas_price=tx['gasPrice'],
                gas_limit=tx['gas'],
                input_data=tx['input'].hex() if tx['input'] else '',
                block_number=tx.get('blockNumber')
            )
        except (TransactionNotFound, Exception):
            return None
    
    def get_eth_balance(self, address: str = None) -> float:
        """Get ETH balance for an address."""
        address = address or self.wallet_address
        balance_wei = self.w3.eth.get_balance(address)
        return self.w3.from_wei(balance_wei, 'ether')
    
    def get_token_balance(self, token_address: str, wallet_address: str = None) -> float:
        """Get ERC20 token balance."""
        wallet_address = wallet_address or self.wallet_address
        
        # ERC20 balanceOf function signature
        contract = self.w3.eth.contract(
            address=token_address,
            abi=[{
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }, {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            }]
        )
        
        try:
            balance = contract.functions.balanceOf(wallet_address).call()
            decimals = contract.functions.decimals().call()
            return balance / (10 ** decimals)
        except Exception as e:
            logger.error("Error getting token balance", 
                        token_address=token_address, error=str(e))
            return 0.0
    
    async def get_token_info(self, token_address: str) -> Optional[TokenInfo]:
        """Get comprehensive token information."""
        try:
            # Standard ERC20 ABI
            erc20_abi = [
                {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
                {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
                {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
                {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
            ]
            
            contract = self.w3.eth.contract(address=token_address, abi=erc20_abi)
            
            # Get basic token info
            name = contract.functions.name().call()
            symbol = contract.functions.symbol().call()
            decimals = contract.functions.decimals().call()
            total_supply = contract.functions.totalSupply().call()
            
            # Get holders count and liquidity from BaseScan API
            holders_count, liquidity_eth = await self._get_token_metrics(token_address)
            
            return TokenInfo(
                address=token_address,
                name=name,
                symbol=symbol,
                decimals=decimals,
                total_supply=total_supply,
                holders_count=holders_count,
                liquidity_eth=liquidity_eth
            )
            
        except Exception as e:
            logger.error("Error getting token info", 
                        token_address=token_address, error=str(e))
            return None
    
    async def _get_token_metrics(self, token_address: str) -> Tuple[int, float]:
        """Get token holders count and liquidity from BaseScan API."""
        try:
            async with aiohttp.ClientSession() as session:
                # Get holders count
                holders_url = f"https://api.basescan.org/api?module=token&action=tokenholderlist&contractaddress={token_address}&page=1&offset=1&apikey={self.config.security.basescan_api_key}"
                
                async with session.get(holders_url) as response:
                    data = await response.json()
                    holders_count = len(data.get('result', []))
                
                # Get liquidity (simplified - would need DEX-specific logic)
                liquidity_eth = 0.0  # Placeholder - implement DEX liquidity checking
                
                return holders_count, liquidity_eth
                
        except Exception as e:
            logger.error("Error getting token metrics", 
                        token_address=token_address, error=str(e))
            return 0, 0.0
    
    def estimate_gas_price(self) -> int:
        """Estimate optimal gas price based on network conditions."""
        try:
            # Get current gas price
            current_gas_price = self.w3.eth.gas_price
            
            # Apply multiplier for faster execution (10% increase)
            optimal_gas_price = int(current_gas_price * 1.1)
            
            # Cap at maximum configured gas price
            max_gas_price_wei = self.w3.to_wei(self.config.gas.max_gas_price_gwei, 'gwei')
            
            return min(optimal_gas_price, max_gas_price_wei)
            
        except Exception as e:
            logger.error("Error estimating gas price", error=str(e))
            return self.w3.to_wei(20, 'gwei')  # Fallback to 20 gwei
    
    def build_transaction(self, to_address: str, data: str = '0x', value: int = 0) -> Dict[str, Any]:
        """Build a transaction with optimal gas settings."""
        nonce = self.w3.eth.get_transaction_count(self.wallet_address, 'pending')
        gas_price = self.estimate_gas_price()
        
        transaction = {
            'to': to_address,
            'value': value,
            'gas': self.config.gas.gas_limit_swap,
            'gasPrice': gas_price,
            'nonce': nonce,
            'data': data,
            'chainId': self.config.network.chain_id
        }
        
        return transaction
    
    def sign_and_send_transaction(self, transaction: Dict[str, Any]) -> str:
        """Sign and send a transaction."""
        try:
            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.config.private_key)
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            logger.info("Transaction sent", 
                       tx_hash=tx_hash.hex(),
                       gas_price=transaction['gasPrice'],
                       nonce=transaction['nonce'])
            
            return tx_hash.hex()
            
        except Exception as e:
            logger.error("Error sending transaction", error=str(e))
            raise
    
    def wait_for_transaction_receipt(self, tx_hash: str, timeout: int = 120) -> Dict[str, Any]:
        """Wait for transaction confirmation."""
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
            
            logger.info("Transaction confirmed", 
                       tx_hash=tx_hash,
                       status=receipt['status'],
                       gas_used=receipt['gasUsed'])
            
            return receipt
            
        except Exception as e:
            logger.error("Error waiting for transaction receipt", 
                        tx_hash=tx_hash, error=str(e))
            raise
    
    async def close(self):
        """Close WebSocket connection."""
        if self.ws_connection:
            await self.ws_connection.close()
            logger.info("WebSocket connection closed")