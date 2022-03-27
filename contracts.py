'''
Defines contract structure for the Dexalot challenge
'''

from web3 import HTTPProvider, Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from web3.middleware import construct_sign_and_send_raw_middleware
import utils 
import requests

ORDER_SIDE_BUY = 0 
ORDER_SIDE_SELL = 1

ORDER_TYPE_MARKET = 0
ORDER_TYPE_LIMIT = 1

ORDER_BOOK_DEPTH_TOP_OF_BOOK = 1
ORDER_BOOK_DEPTH_BEST_PRICE = 2

class Contracts :
    last_buy_order_id = "" 
    last_sell_order_id = ""  

    # initate web3 request with rpc 
    def __init__(self, logger, rpc_url, sender_address, private_key, token_pair, pairs):
        self.logger = logger 
        self.rpc_url = rpc_url
        self.sender_address = sender_address
        self.private_key = private_key
        self.pairs = pairs 
        self.default_token_pair = token_pair 

        self.web3 = Web3(HTTPProvider(rpc_url))
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.register_private_key(private_key)
    
    # registers web3 private key 
    def register_private_key(self, private_key):
        assert (isinstance(self.web3, Web3))
        account = Account.privateKeyToAccount(private_key)
        self.web3.middleware_onion.add(construct_sign_and_send_raw_middleware(account))
        self.web3.eth.default_account = account.address    

    # get all reference data for contracts
    def load_reference_data(self) :
        # define list of relevant reference data to retrieve 
        deployTypes = ["Exchange", "Portfolio", "TradePairs", "OrderBooks"]
        self.deployments, self.contracts = {}, {}
        # for each type, request reference data from dexalot api 
        for deployType in deployTypes:
            deploy = requests.get("https://api.dexalot-dev.com/api/trading/deploymentabi/%s" % deployType).json()
            self.deployments[deployType] = deploy 
            self.contracts[deployType] = self.web3.eth.contract(address=deploy["address"], abi=deploy["abi"]["abi"])

    def get_contract_exchange(self) :
        return self.contracts["Exchange"]

    def get_contract_portfolio(self) :
        return self.contracts["Portfolio"]

    def get_contract_order_books(self) :
        return self.contracts["Orderbooks"]

    def get_contract_trade_pairs(self) :
        return self.contracts["TradePairs"]

    # builds transaction by combining default params with override key values 
    def built_transaction(self, override=None) :
        # default params for transaction 
        params = {
            "nonce": self.web3.eth.get_transaction_count(self.web3.eth.default_account),
            'gas': 2000000,
            'gasPrice': self.web3.toWei('100', 'gwei'),
            #'gas': web3.eth.generate_gas_price(txn),
            #'gasPrice': web3.eth.estimate_gas(txn),
        }
        # for each key value in override, update params 
        if override is not None :
            for k in override.keys() :
                params[k] = override[k]
                
        return params        

    def format_decimal_quote(self, value, token_pair=None) :
        if token_pair is None :
            token_pair = self.default_token_pair

        return utils.to_wei(value, self.pairs[token_pair]["quote_evmdecimals"], self.pairs[token_pair]["quotedisplaydecimals"])

    def format_decimal_base(self, value, token_pair=None) :
        if token_pair is None :
            token_pair = self.default_token_pair

        return utils.to_wei(value, self.pairs[token_pair]["base_evmdecimals"], self.pairs[token_pair]["basedisplaydecimals"])

    def parse_decimal_quote(self, value, token_pair=None) :
        if token_pair is None :
            token_pair = self.default_token_pair

        return utils.from_wei(value, self.pairs[token_pair]["quote_evmdecimals"], self.pairs[token_pair]["quotedisplaydecimals"])

    def parse_decimal_base(self, value, token_pair=None) :
        if token_pair is None :
            token_pair = self.default_token_pair

        return utils.from_wei(value, self.pairs[token_pair]["base_evmdecimals"], self.pairs[token_pair]["basedisplaydecimals"])

    # get AVAX balance for current account wallet
    def get_balance(self): 
        return self.web3.fromWei(self.web3.eth.get_balance(self.sender_address), 'ether')    

    # deposit tokens from wallet into portfolio
    def deposit_token(self, fromAddress, symbol, quantity):
        contract = self.get_contract_portfolio()

        fromAddress = Web3.toChecksumAddress(fromAddress)
        symbol = self.web3.toBytes(text=symbol)
        quantity = self.format_decimal_base(quantity)

        txn = contract.functions.depositToken(fromAddress, symbol, quantity)
        txn = txn.buildTransaction(self.built_transaction())
        signed_txn = self.web3.eth.account.sign_transaction(txn, private_key=self.private_key)
        tx_token = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)   

        txn_receipt = self.web3.eth.waitForTransactionReceipt(tx_token)
        self.logger.debug("deposit_token", str(fromAddress), str(symbol), str(quantity), str(txn_receipt))

        return tx_token

    # for a trading pair, cancel single order given id of order 
    def cancel_order(self, order_id, teamPair) :
        contract = self.get_contract_trade_pairs()

        txn = contract.functions.cancelOrder(self.web3.toBytes(text=teamPair), order_id)
        txn = txn.buildTransaction(self.built_transaction())
        signed_txn = self.web3.eth.account.sign_transaction(txn, private_key=self.private_key)
        tx_token = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)

        txn_receipt = self.web3.eth.waitForTransactionReceipt(tx_token)
        self.logger.debug("cancel_order", str(order_id), str(teamPair), str(txn_receipt))

        return tx_token 

    # for a trading pair, cancel list of orders given their ids 
    def cancel_all_orders(self, order_ids, teamPair) :
        contract = self.get_contract_trade_pairs()

        txn = contract.functions.cancelAllOrders(self.web3.toBytes(text=teamPair), order_ids)
    
        txn = txn.buildTransaction(self.built_transaction())
        signed_txn = self.web3.eth.account.sign_transaction(txn, private_key=self.private_key)
        tx_token = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)

        txn_receipt = self.web3.eth.waitForTransactionReceipt(tx_token)
        self.logger.debug("cancel_all_orders", str(order_ids), str(teamPair), str(txn_receipt))

        return tx_token 

    # for given trading pair id, get symbol 
    def get_symbol(self, tradePairId, isBase):
        contract = self.get_contract_exchange()
        return contract.functions.getSymbol(self.web3.toBytes(text=tradePairId), isBase).call()

    # add a new order to the order book for a trade pair
    def add_order(self, trade_pair_id, price, quantity, order_side, order_type):
        contract = self.get_contract_trade_pairs()

        price = self.format_decimal_quote(price)
        quantity = self.format_decimal_base(quantity)

        txn = contract.functions.addOrder(self.web3.toBytes(text=trade_pair_id), price, quantity, order_side, order_type)

        txn = txn.buildTransaction(self.built_transaction())
        signed_txn = self.web3.eth.account.sign_transaction(txn, private_key=self.private_key)
        tx_token = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)

        txn_receipt = self.web3.eth.waitForTransactionReceipt(tx_token)
        self.logger.debug("add_order", str(trade_pair_id), str(price), str(quantity), str(order_side), str(order_type), str(txn_receipt))

        return tx_token

    # for given order id, get array of order details 
    def get_order(self, order_id) :
        contract = self.get_contract_trade_pairs()

        tx = contract.functions.getOrder(order_id).call()
    
        resp = {      
            "id": tx[0],
            "price": tx[1],
            "totalAmount": tx[2],
            "quantity": tx[3],
            "quantityFilled": tx[4],
            "totalFee": tx[5],
            "traderaddress": tx[6],
            "side": tx[7],
            "type1": tx[8],
            "status": tx[9],       
        }
        return resp 

    # get the buy order book from the block chain
    def getOrderBookBuy(self, trade_pair_id, req_depth) :
        contract = self.get_contract_trade_pairs() 

        res = contract.functions.getNBuyBook(self.web3.toBytes(text=trade_pair_id), req_depth, 0, 0, self.last_buy_order_id).call()

        orders = [] 

        if len(res[0]) > 0 :
            for f in res[0] :
                if f != 0 :
                    orders.append(f)

        if len(res[1]) > 0 :
            for f in res[1] :
                if f != 0 :
                    orders.append(f)

        if len(orders) > 0 :
            cur_price = res[2]
            self.last_buy_order_id = res[3]  
        else :
            cur_price = 0 

        return orders, cur_price

    # get the sell order book from the block chain
    def getOrderBookSell(self, trade_pair_id, req_depth) :
        
        contract = self.get_contract_trade_pairs() 

        res = contract.functions.getNSellBook(self.web3.toBytes(text=trade_pair_id), req_depth, 0, 0, self.last_sell_order_id).call()

        orders = [] 

        if len(res[0]) > 0 :
            for f in res[0] :
                if f != 0 :
                    orders.append(f)

        if len(res[1]) > 0 :
            for f in res[1] :
                if f != 0 :
                    orders.append(f) 

        if len(orders) > 0 :
            cur_price = res[2]
            self.last_sell_order_id = res[3] 
        else :
            cur_price = 0                

        return orders, cur_price  

    # for given id of trading pair, get auction data 
    def getAuctionData(self, trade_pair_id) :
        contract = self.get_contract_trade_pairs() 

        return contract.functions.getAuctionData(self.web3.toBytes(text=trade_pair_id)).call()
        


        