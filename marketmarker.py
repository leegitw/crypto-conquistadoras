from ast import Or
import contracts 
import api 
import utils 
import random
import math 
import os 
import pandas as pd 

class OrderRequest :
    price = None 
    quantity = None   
    est_gas = None   

    # validate the quantity
    def validate(self, mintrade_amnt, maxtrade_amnt, increment=0): 
        amount = self.amount()

        # ensure the quantity meets the minumim trade amount
        if increment > 0 : 
            while amount < mintrade_amnt :
                self.quantity = self.quantity + increment
                amount = self.amount()
        else :
            if amount < mintrade_amnt :
                raise Exception("amount less than min")         
            
        # ensure the quantity does not exceed the maximum trade amout 
        if amount > maxtrade_amnt :
            raise Exception("amount exceeded max") 

    def amount(self) :
        return self.price * self.quantity     

class OrderParams:
    bid_price_raw = None 
    bid_price = None 
    ask_price_raw = None 
    ask_price = None 
    mid_price = None 
    spread_amount = None
    avg_price = None
    avg_spread = None
    base_price = None
    min_spread_amount = None
    max_spread_amount = None
    target_spread_amount = None
    mintrade_amnt = None
    maxtrade_amnt = None
    est_gas_price = None 
    buy_request : OrderRequest = None 
    sell_request : OrderRequest = None     

class MarketMaker :
    def __init__(self, logger, teamPair, contracts: contracts.Contracts, api: api.Api):
        self.logger = logger 
        self.teamPair = teamPair
        self.contracts = contracts
        self.api = api
        self.order_book_df = None 
        self.cur_open_orders = {}

        # get token symbols and symbol names
        self.teamSymbolName = teamPair.split("/")[0]
        self.nativeSymbolName = teamPair.split("/")[1]
        
        # load the native symbol
        self.nativeSymbol = self.contracts.get_symbol(self.teamPair, False)
        self.logger.info("nativeSymbol %s" % self.nativeSymbolName)
        
        # load the team symbol
        self.teamSymbol = self.contracts.get_symbol(self.teamPair, True)
        self.logger.info("teamSymbol %s" % self.teamSymbolName)

    def load_open_orders(self) :
        res = self.api.openOrders(self.contracts.sender_address, self.teamPair)

        for order in res["rows"] :
            self.cur_open_orders[order['id']] = order 

        return self.cur_open_orders

    def generate_order_params(self, initial_price=2.0, default_quantity=2) :

        # bid is the maximum price that a buyer is willing to pay
        _, bid_price_raw = self.contracts.getOrderBookBuy(self.teamPair, contracts.ORDER_BOOK_DEPTH_TOP_OF_BOOK)
        bid_price = self.contracts.parse_decimal_quote(bid_price_raw)
        self.logger.info("bid_price %.4f bid_price_raw %.4f" % (bid_price, bid_price_raw))

        # ask is the minimum price that a seller is willing to accept 
        _, ask_price_raw = self.contracts.getOrderBookSell(self.teamPair, contracts.ORDER_BOOK_DEPTH_TOP_OF_BOOK)
        ask_price = self.contracts.parse_decimal_quote(ask_price_raw)
        self.logger.info("ask_price %.4f ask_price_raw %.4f" % (ask_price, ask_price_raw))

        mid_price = None 
        spread_amount = 0 
        if bid_price > 0.01 and ask_price > 0.01 :
            mid_price = (bid_price + ask_price) / 2
            spread_amount = ask_price - bid_price
        elif bid_price > 0.01 :
            mid_price = bid_price
        elif ask_price > 0.01 :
            mid_price = ask_price   
        else :
            # TODO: should log all the past orders and to generate a last price
            #       that can be used as reference  
            mid_price = initial_price

        # TODO: finish this!!!!
        self.log_order_book(mid_price, spread_amount)

        avg_price = self.avg_mid_price()
        avg_spread = self.avg_spread_amount()

        base_price = avg_price
        if base_price == 0 :
            base_price = mid_price

        buy_gas = self.contracts.estimate_order_gas(self.teamPair, base_price, default_quantity, contracts.ORDER_SIDE_BUY, contracts.ORDER_TYPE_LIMIT)
        self.logger.debug(f"buy Est. Gas:  {buy_gas}")

        sell_gas = self.contracts.estimate_order_gas(self.teamPair, base_price, default_quantity, contracts.ORDER_SIDE_SELL, contracts.ORDER_TYPE_LIMIT)
        self.logger.debug(f"sell Est. Gas:  {sell_gas}")
        
        est_gas = self.contracts.parse_decimal_quote(buy_gas + sell_gas, display_decimals=10)
        
        # ensure the spread is at least wide enough to cover gas fees 
        min_spread_amount = 0.1 + est_gas

        if avg_spread > 0 :
            max_spread_amount = min_spread_amount + (avg_spread / 2)
        else :
            max_spread_amount = min_spread_amount + 0.02

        if max_spread_amount - min_spread_amount < 0.05 :
            max_spread_amount = max_spread_amount + 0.05    

        target_spread_amount = random.uniform(min_spread_amount, max_spread_amount)
        #target_spread_amount = max_spread_amount

        self.logger.info("avg_price %.2f" % (avg_price))
        self.logger.info("base_price %.2f" % (base_price))
        self.logger.info("avg_spread %.2f" % (avg_spread))
        self.logger.info("min_spread_amount %.2f" % (min_spread_amount))
        self.logger.info("max_spread_amount %.2f" % (max_spread_amount))
        self.logger.info("target_spread_amount %.2f" % (target_spread_amount))

        trading_pair = self.api.trading_pair(self.teamPair)
        mintrade_amnt = float(trading_pair['mintrade_amnt'])
        maxtrade_amnt = float(trading_pair['maxtrade_amnt'])
        self.logger.info("mintrade_amnt %.2f" % (mintrade_amnt))
        self.logger.info("maxtrade_amnt %.2f" % (maxtrade_amnt))
        
        resp = OrderParams()
        resp.bid_price_raw = bid_price_raw 
        resp.bid_price = bid_price 
        resp.ask_price_raw = ask_price_raw 
        resp.ask_price = ask_price 
        resp.mid_price = mid_price 
        resp.spread_amount = spread_amount
        resp.avg_price = avg_price
        resp.avg_spread = avg_spread
        resp.base_price = base_price
        resp.min_spread_amount = min_spread_amount
        resp.max_spread_amount = max_spread_amount
        resp.target_spread_amount = target_spread_amount
        resp.mintrade_amnt = mintrade_amnt
        resp.maxtrade_amnt = maxtrade_amnt
        resp.est_gas_price = est_gas
        
        # buy: compute entry prices 
        buy_request = OrderRequest()
        buy_request.price = base_price - target_spread_amount 
        buy_request.quantity = default_quantity
        buy_request.est_gas = buy_gas
        self.logger.info("buy_request.amount %.10ff" % (buy_request.amount()))
        buy_request.validate(mintrade_amnt, maxtrade_amnt, increment=1)
        resp.buy_request = buy_request
        
        # sell: compute entry prices 
        sell_request = OrderRequest()
        sell_request.price = base_price + target_spread_amount 
        sell_request.quantity = default_quantity
        sell_request.est_gas = sell_gas
        self.logger.info("sell_request.amount %.10ff" % (sell_request.amount()))  
        sell_request.validate(mintrade_amnt, maxtrade_amnt, increment=1)
        resp.sell_request = sell_request
      
        if resp.sell_request.quantity > resp.buy_request.quantity :
            resp.buy_request.quantity = resp.sell_request.quantity
        elif resp.buy_request.quantity > resp.sell_request.quantity:
            resp.sell_request.quantity = resp.buy_request.quantity

        return resp 

    def execute_buy_order(self, req : OrderRequest, order_type=contracts.ORDER_TYPE_LIMIT) :

        #if order_type == contracts.ORDER_TYPE_MARKET :
        #    req.price = 0 

        order_side = contracts.ORDER_SIDE_BUY
        
        tx_token = self.contracts.add_order(self.teamPair, req.price, req.quantity, order_side, order_type)
        self.logger.info("execute_buy_order price:%.2f quantity:%.0f tx:%s" % (req.price, req.quantity, tx_token))

        # TODO: add the order to the local cur_open_orders for reference 

        return tx_token

    def execute_sell_order(self, req : OrderRequest, order_type=contracts.ORDER_TYPE_LIMIT) :

        #if order_type == contracts.ORDER_TYPE_MARKET :
        #    req.price = 0 

        order_side = contracts.ORDER_SIDE_SELL
        
        tx_token = self.contracts.add_order(self.teamPair, req.price, req.quantity, order_side, order_type)
        self.logger.info("execute_sell_order price:%.2f quantity:%.0f tx:%s" % (req.price, req.quantity, tx_token))

        # TODO: add the order to the local cur_open_orders for reference 

        return tx_token

    def cancel_order(self, order_id) :
        tx_token = self.contracts.cancel_order(order_id, teamPair=self.teamPair)

        # remove the order from the current open orders
        if order_id in self.cur_open_orders.keys() :
            del self.cur_open_orders[order_id]

    def cancel_all_orders(self, order_ids) :
        tx_token = self.contracts.cancel_all_orders(order_ids, teamPair=self.teamPair)

        # remove the orders from the current open orders
        for order_id in order_ids :
            if order_id in self.cur_open_orders.keys() :
                del self.cur_open_orders[order_id]    

    # log order meta to a panda dataframe for runtime stats
    def log_order_book(self, mid_price, spread_amount) :
        
        row = {'mid_price': mid_price, 'spread_amount': spread_amount}

        if self.order_book_df is None :
            # create the pandas DataFrame
            self.order_book_df = pd.DataFrame([], columns = row.keys())

        row_df = pd.DataFrame([row])
        self.order_book_df = pd.concat([self.order_book_df, row_df], ignore_index=False)
        return self.order_book_df

    # compute the average mid price for the last N periods
    def avg_mid_price(self, window=5) :
        avg = self.order_book_df['mid_price'].rolling(window).mean().tail(1).values[0]
    
        if math.isnan(avg) :
            avg = 0 

        return float(avg)    

    # compute the average spread amounts for the last N periods
    def avg_spread_amount(self, window=5) :
        avg = self.order_book_df['spread_amount'].rolling(window).mean().tail(1).values[0]
        
        if math.isnan(avg) :
            avg = 0 

        return float(avg)            
        