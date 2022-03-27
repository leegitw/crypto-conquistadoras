'''
Main script for the Dexalot challenge.

 /$$$$$$$                                /$$             /$$                  
| $$__  $$                              | $$            | $$                  
| $$  \ $$  /$$$$$$  /$$   /$$  /$$$$$$ | $$  /$$$$$$  /$$$$$$                
| $$  | $$ /$$__  $$|  $$ /$$/ |____  $$| $$ /$$__  $$|_  $$_/                
| $$  | $$| $$$$$$$$ \  $$$$/   /$$$$$$$| $$| $$  \ $$  | $$                  
| $$  | $$| $$_____/  >$$  $$  /$$__  $$| $$| $$  | $$  | $$ /$$              
| $$$$$$$/|  $$$$$$$ /$$/\  $$|  $$$$$$$| $$|  $$$$$$/  |  $$$$/              
|_______/  \_______/|__/  \__/ \_______/|__/ \______/    \___/                


  /$$$$$$  /$$                 /$$ /$$                                        
 /$$__  $$| $$                | $$| $$                                        
| $$  \__/| $$$$$$$   /$$$$$$ | $$| $$  /$$$$$$  /$$$$$$$   /$$$$$$   /$$$$$$ 
| $$      | $$__  $$ |____  $$| $$| $$ /$$__  $$| $$__  $$ /$$__  $$ /$$__  $$
| $$      | $$  \ $$  /$$$$$$$| $$| $$| $$$$$$$$| $$  \ $$| $$  \ $$| $$$$$$$$
| $$    $$| $$  | $$ /$$__  $$| $$| $$| $$_____/| $$  | $$| $$  | $$| $$_____/
|  $$$$$$/| $$  | $$|  $$$$$$$| $$| $$|  $$$$$$$| $$  | $$|  $$$$$$$|  $$$$$$$
 \______/ |__/  |__/ \_______/|__/|__/ \_______/|__/  |__/ \____  $$ \_______/
                                                           /$$  \ $$          
                                                          |  $$$$$$/          
                                                           \______/           
'''

import requests 
from decimal import Decimal
import marketmarker
import api 
import contracts
import signal
import requests
import os
import time 
import json 

import logging
logger = logging.getLogger('marketmarker')
hdlr = logging.FileHandler('dexalot.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)


# this signal handler allows for a graceful shutdown when CTRL+C is pressed
def signal_handler(signum, frame):
    global shutdown
    print("Shutting down...")
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    shutdown = True

# get Reference Data from the RESTAPI (contract addresses, pairs, trade increments, min, max trade amount) 
def challengeLoadReferenceData(web3 : contracts.Contracts) :
    try :
        print("Loading Reference Data...")

        web3.load_reference_data()
        print("✔\tReference Data\t\t20 points")
    except Exception as e: 
        print("𐄂\tReference Data\t\t0 points\n\t\terror:", str(e))    

# deposit Avax and Team3 automatically
def challenge1DespositToken(marketMaker: marketmarker.MarketMaker, despositAmount: int) :
    try :
        print("Deposit Tokens Automatically...")

        marketMaker.contracts.deposit_token(marketMaker.contracts.sender_address, marketMaker.nativeSymbolName, despositAmount)
        print("\tMaking deposit to %s"% marketMaker.nativeSymbolName)

        marketMaker.contracts.deposit_token(marketMaker.contracts.sender_address, marketMaker.teamSymbolName, despositAmount)
        print("\tMaking deposit to %s"% marketMaker.teamSymbolName)

        print("✔\tDesposit Tokens Automatically\t\t5 points")
    except Exception as e: 
        print("𐄂\tDesposit Tokens Automatically\t\t0 points\n\t\terror:", str(e))   

# called on startup
def challengeStartupLoad(marketMaker: marketmarker.MarketMaker) :
    try :
        print("Loading Open Orders...")

        # get open orders at startup 
        orders = marketMaker.load_open_orders()

        if len(orders) == 0 :
            raise Exception("no open orders")

        print("✔\tLoaded %d Open Orders\t\t20 points" % len(orders))
    except Exception as e: 
        print("𐄂\tReference Data\t\t0 points\n\t\terror:", str(e))   

    return orders

# create list of order_ids from provided orders and any partially filled orders
def group_cancel_orders(orders) :
    order_ids = []
    partial_orders = {}
    for order_id in orders.keys(): 
        order = orders[order_id]

        skip = False
        if order["status"] == 1 :
            # REJECTED - no need to cancel
            skip = True
        elif order["status"] == 2 :
            # PARTIAL - must cancel and then reverse order
            skip = False 

            if float(order["quantityfilled"]) > 0 and float(order["quantityfilled"]) < float(order["quantity"]) :
                partial_orders[order_id] = order 
        elif order["status"] == 3 :
            # FILLED - no need to cancel
            skip = True
        elif order["status"] == 4 :
            # CANCELED - no need to cancel
            skip = True
        elif order["status"] == 6 :
            # KILLED - no need to cancel

            if order["quantityfilled"] == 0 :
                skip = True
        if skip :
            continue        
    
        order_ids.append(order_id)

    return order_ids, partial_orders 

# use a market order to reverse any partial filled orders
def reverse_order_partial_fill(marketMaker: marketmarker.MarketMaker, orig_order) :

    order_id = orig_order["id"]
    
    # get the updated order to ensure no new fills 
    new_order = marketMaker.contracts.get_order(order_id)

    # when filled doesn't match quantity then need to reverse the order
    if float(new_order["quantityfilled"]) == 0 or float(new_order["quantityfilled"]) >= float(new_order["quantity"]) :
        return 0 
        
    req = marketmarker.OrderRequest()
    req.quantity = float(new_order["quantity"] - new_order["quantityfilled"])

    # Note: this price should be updated to the current market price
    #       market orders don't seem to work
    req.price = float(new_order["price"])

    if new_order["side"] == contracts.ORDER_SIDE_BUY :
        marketMaker.execute_sell_order(req)
    else :
        marketMaker.execute_buy_order(req)
                
    return req.quantity            

# cancel open orders given orders
# reverse any portion that has been filled
def challengeCancelOpenOrders(marketMaker: marketmarker.MarketMaker, orders) :

    # for testing only
    if False :
        challengeOrderSet1(marketMaker)

        time.sleep(5)
        orders = challengeStartupLoad(marketMaker=marketMaker)

        for order_id in orders.keys() :
            order = orders[order_id]

            req = marketmarker.OrderRequest()
            req.quantity = 1
            req.price = float(order["price"])

            if int(order["side"]) == contracts.ORDER_SIDE_BUY :
                marketMaker.execute_sell_order(req)
                print("sell partial", order_id, "quant", order["quantity"])
            else :
                marketMaker.execute_buy_order(req)
                print("buy partial", order_id, "quant", order["quantity"])
            
        print("check orders!!!!")    
        time.sleep(10)
        orders = challengeStartupLoad(marketMaker=marketMaker)

    order_ids, partial_orders = group_cancel_orders(orders)    
   
    try :
        print("Canceling %d Open Orders..." % len(order_ids))

        if len(order_ids) == 0 :
            raise Exception("no open orders to cancel")

        # for each order, cancel it 
        for order_id in order_ids:
            print("\t\tOrder %s Canceled"% (order_id))
            marketMaker.cancel_order(order_id)

            if order_id in partial_orders.keys() :
                orig_order = partial_orders[order_id]
                print("\t\tOrder %s Partilly Filled %s of %s" % (order_id, orig_order["quantityfilled"], orig_order["quantity"]))
                
                reverse_quantity = reverse_order_partial_fill(marketMaker, orig_order)
                print("\t\t\treversed %.2f with market order" % reverse_quantity)
                    
        print("✔\tCanceled %d Open Orders\t\t5 points" % len(order_ids))
    except Exception as e: 
        print("𐄂\tCancel %d Open Orders\t\t0 points\n\t\terror:" % len(order_ids), str(e))  
        raise e  

# enter a BUY & a SELL order with a predefined spread around a given mid price
# or last price against the contracts. 
def challengeOrderSet1(marketMaker: marketmarker.MarketMaker) :
    try :
        print("First Buy & Sell Orders...")

        params = marketMaker.generate_order_params()

        # excute the buy order 
        buy_token = marketMaker.execute_buy_order(params.buy_request)
        print("\t\tCreated Buy Order at $%.2f for %d shares"% (params.buy_request.price, params.buy_request.quantity))

        # excute the sell order 
        sell_token = marketMaker.execute_sell_order(params.sell_request)
        print("\t\tCreated Sell Order at $%.2f for %d shares"% (params.sell_request.price, params.sell_request.quantity))
            
        print("✔\tFirst Buy & Sell Orders\t\t20 points")
    except Exception as e: 
        print("𐄂\tFirst Buy & Sell Orders\t\t0 points\n\t\terror:", str(e))   
        params = None 
        raise e 

    return params

# enter a new set of buy & sell orders with different prices based on the changing 
# mid/last price  against the contracts 
def challengeOrderSet2(marketMaker: marketmarker.MarketMaker, cache) :

    try :
        print("Second Buy & Sell Orders...")

        params = marketMaker.generate_order_params()

        # verify buy is different than first
        if cache["set1_buy_request_price"] != params.buy_request.price :
            print("\t\tBuy price changed from %.2f to %.2f" % (cache["set1_buy_request_price"], params.buy_request.price ))

        # excute the buy order 
        buy_token = marketMaker.execute_buy_order(params.buy_request)
        print("\t\tBuy Order created at $%.2f for %d shares"% (params.buy_request.price, params.buy_request.quantity))

        # verify sell is different than first
        if cache["set1_sell_request_price"] != params.sell_request.price :
            print("\t\tSell price changed from %.2f to %.2f" % (cache["set1_sell_request_price"], params.sell_request.price ))

        # excute the sell order 
        sell_token = marketMaker.execute_sell_order(params.sell_request)
        print("\t\tSell Order created at $%.2f for %d shares"% (params.sell_request.price, params.sell_request.quantity))
        
        print("✔\tSecond Buy & Sell Orders\t\t20 points")


        # Get gas cost of each order and log it before in order to make buy/sell decisions 
        # with t-cost in mind (and console.log it ). 
        print("Estimate Order Gas...")
        print("\t\tBuy order gas %.2f" % (params.buy_request.est_gas))
        print("\t\tSell order gas %.2f" % (params.sell_request.est_gas))

        print("\t\tTotal estimated gas %.20f in terms of price" % (params.est_gas_price))
        if params.target_spread_amount > params.est_gas_price :
            print("\t\tTarget spread %.20f GREATER than estimated gas %.20f price" % (params.target_spread_amount, params.est_gas_price))
            print("✔\tEstimate Order Gas\t\t10 points")
        else :
            print("\t\tTarget spread %.20f GREATER than estimated gas %.20f price" % (params.target_spread_amount, params.est_gas_price))
            print("𐄂\tEstimate Order Gas\t\t0 points")     

    except Exception as e: 
        print("𐄂\tSecond Buy & Sell Orders\t\t0 points\n\t\terror:", str(e))   
    
# get order book for buy and sell orders 
def challengeBonusPrintOrderBook(marketMaker: marketmarker.MarketMaker) :
    # this is broken
    return 

    # get order by id and print array of data for order 
    def printOrder(order_id) :
        order = marketMaker.contracts.get_order(order_id)
        print("\t\t", json.dumps(order))

    try :
        print("Print Order Book...")

        open_cnt = 0

        # retrieve buy orders in top of book 
        buyOrders, _ = marketMaker.contracts.getOrderBookBuy(marketMaker.teamPair, contracts.ORDER_BOOK_DEPTH_TOP_OF_BOOK)
        print("\t\tBuy Orders:")
        for order_id in buyOrders :
            open_cnt = open_cnt + 1
            printOrder(order_id) 
        
        # retrieve sell orders in top of book 
        sellOrders, _ = marketMaker.contracts.getOrderBookSell(marketMaker.teamPair, contracts.ORDER_BOOK_DEPTH_TOP_OF_BOOK)
        print("\t\tSell Orders:")
        for order_id in sellOrders :
            open_cnt = open_cnt + 1
            printOrder(order_id) 

        if open_cnt < 2 :
            raise Exception("open count %d less than 2" % open_cnt)    

        print("✔\tPrint Order Book\t\t10 points")
    except Exception as e: 
        print("𐄂\tPrint Order Book\t\t0 points\n\t\t", str(e))

# cancel all open orders 
def challengeCancelAllOpenOrders(marketMaker: marketmarker.MarketMaker) :

    # for testing only
    if False :
        challengeOrderSet1(marketMaker)

        time.sleep(5)
        orders = challengeStartupLoad(marketMaker=marketMaker)

        for order_id in orders.keys() :
            order = orders[order_id]

            req = marketmarker.OrderRequest()
            req.quantity = 1
            req.price = float(order["price"])

            if int(order["side"]) == contracts.ORDER_SIDE_BUY :
                marketMaker.execute_sell_order(req)
                print("sell partial", order_id, "quant", order["quantity"])
            else :
                marketMaker.execute_buy_order(req)
                print("buy partial", order_id, "quant", order["quantity"])
            
        print("check orders!!!!")    
        time.sleep(10)
        orders = challengeStartupLoad(marketMaker=marketMaker)

    try :
        print("Cancel All Open Orders...")

        # load all open orders 
        res = marketMaker.api.openOrders(marketMaker.contracts.sender_address, marketMaker.teamPair)

        # generate a list of open orders
        orders = {}
        for row in res["rows"] :
            orders[row["id"]] = row 

        order_ids, partial_orders  = group_cancel_orders(orders)

        if len(order_ids) > 0:
            # execute the cancel all
            marketMaker.cancel_all_orders(order_ids)

            # handle partially filled orders here!
            for order_id in order_ids :
                print("\t\tOrder %s Canceled"% (order_id))
                
                if order_id in partial_orders.keys() :
                    orig_order = partial_orders[order_id]
                    print("\t\tOrder %s Partilly Filled %s of %s" % (order_id, orig_order["quantityfilled"], orig_order["quantity"]))
                    
                    reverse_quantity = reverse_order_partial_fill(marketMaker, orig_order)
                    print("\t\t\treversed %.2f with market order" % reverse_quantity)
        
        print("✔\tCanceled All Open Orders\t\t15 points")
    except Exception as e: 
        print("𐄂\tCancel All Open Orders\t\t0 points\n\t\terror:", str(e))
        raise e 

# this is the main method containing the actual market making strategy logic
def main():

    # team specific configuration parameters 
    team_name = "TEAM3"
    team_pair = "TEAM3/AVAX"
    deposit_amount = 10 
    rpc_url = 'https://node.dexalot-dev.com/ext/bc/C/rpc'

    # use input prompt to collect metamask wallet address and private key
    sender_address = os.environ.get("SENDER_ADDRESS") 
    if sender_address is None or sender_address == "" :
        sender_address = input("Enter your metamask(or other wallet) address")

    private_key = os.environ.get("PRIVATE_KEY") 
    if private_key is None or private_key == "" :
        private_key = input("Enter Your metamask(or other wallet) private key")

    # init a new api client
    api_client = api.Api(logger, teamName=team_name, teamPair=team_pair)

    # load the trade pairs
    pairs = api_client.trading_pairs()

    # init a new web3 client for handling the contracts
    web3 = contracts.Contracts(logger, rpc_url, sender_address, private_key, team_pair, pairs)

    # Get Reference Data from the RESTAPI (contract addresses, pairs, trade increments, min, max trade amount) 
    # 20 points 
    challengeLoadReferenceData(web3)

    # init the market marker
    marketMaker = marketmarker.MarketMaker(logger, teamPair=team_pair, contracts=web3, api=api_client)

    # file used to persist if the first have of the challenge has been completed.
    init_file = "./init_challenge_par1-v11"
    if os.path.exists(init_file) :
        # Read & print the entire file 
        with open(init_file, 'r') as reader:
            cache = json.loads(reader.read())

        # Get your open orders from RESTAPI at startup. 
        # 20 points
        orders = challengeStartupLoad(marketMaker=marketMaker)

        # temp for testing
        #if len(orders) == 0 :
        #    challengeOrderSet1(marketMaker) 
        #    orders = challengeStartupLoad(marketMaker=marketMaker)
        
        # Wait ~10 seconds and Cancel Buy & Sell your previously opened orders. if you can foresee & mitigate a potential issue in the previous step.  
        # 5 points (mitigating code to be submitted in an email)
        time.sleep(10)
        challengeCancelOpenOrders(marketMaker=marketMaker, orders=orders)

        # Wait ~20 seconds and enter a new set of buy & sell orders  with different prices based on the changing mid/last price  against the contracts 
        # 20 points
        time.sleep(20)
        challengeOrderSet2(marketMaker=marketMaker, cache=cache)

        # Bonus: print order bool to console log 
        # 10 points
        challengeBonusPrintOrderBook(marketMaker)

        # Wait ~30 seconds and CancelAll all your open orders using CancelAll against the contracts 
        # 15 points
        time.sleep(30)
        challengeCancelAllOpenOrders(marketMaker=marketMaker)
    else :
        # Start with depositing your tokens from the frontend (See bonus items)
        challenge1DespositToken(marketMaker=marketMaker, despositAmount=deposit_amount)

        # Enter a BUY & a SELL order with a predefined spread around a given mid price or last price against the contracts. (Keep orders in an internal map) 
        # 20 points
        order_params = challengeOrderSet1(marketMaker)

        if order_params is not None : 
            # write a file so we know the first challenge has run
            cache = {
                "set1_buy_request_price": order_params.buy_request.price,
                "set1_sell_request_price": order_params.sell_request.price,
            }
            with open(init_file, 'w') as f:
                f.write(json.dumps(cache))

# this calls the main() method
if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    print('''\

 /$$$$$$$                                /$$             /$$    
| $$__  $$                              | $$            | $$    
| $$  \ $$  /$$$$$$  /$$   /$$  /$$$$$$ | $$  /$$$$$$  /$$$$$$  
| $$  | $$ /$$__  $$|  $$ /$$/ |____  $$| $$ /$$__  $$|_  $$_/  
| $$  | $$| $$$$$$$$ \  $$$$/   /$$$$$$$| $$| $$  \ $$  | $$    
| $$  | $$| $$_____/  >$$  $$  /$$__  $$| $$| $$  | $$  | $$ /$$
| $$$$$$$/|  $$$$$$$ /$$/\  $$|  $$$$$$$| $$|  $$$$$$/  |  $$$$/
|_______/  \_______/|__/  \__/ \_______/|__/ \______/    \___/                                                          

    ''')
    print("starting money printer...")
    print("brrrr...")
    print("")
    main()