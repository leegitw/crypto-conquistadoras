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
    except Exception as e: # work on python 3.x
        print("𐄂\tReference Data\t\t0 points", str(e))    

# deposit Avax and Team3 automatically
def challenge1DespositToken(marketMaker: marketmarker.MarketMaker, despositAmount: int) :
    try :
        print("Deposit Tokens Automatically...")

        marketMaker.contracts.deposit_token(marketMaker.contracts.sender_address, marketMaker.nativeSymbolName, despositAmount)
        print("\tMaking deposit to %s"% marketMaker.nativeSymbolName)

        marketMaker.contracts.deposit_token(marketMaker.contracts.sender_address, marketMaker.teamSymbolName, despositAmount)
        print("\tMaking deposit to %s"% marketMaker.teamSymbolName)

        print("✔\tDesposit Tokens Automatically\t\t5 points")
    except Exception as e: # work on python 3.x
        print("𐄂\tDesposit Tokens Automatically\t\t0 points", str(e))   

# called on startup
def challengeStartupLoad(marketMaker: marketmarker.MarketMaker) :
    try :
        print("Loading Open orders...")

        # get open orders at startup 
        orders = marketMaker.load_open_orders()

        print("✔\tOpen Orders\t\t20 points")
    except Exception as e: # work on python 3.x
        print("𐄂\tReference Data\t\t0 points", str(e))   

    return orders

# cancel open orders given orders
# reverse any portion that has been filled
def challengeCancelOpenOrders(marketMaker: marketmarker.MarketMaker, orders) :
    try :
        # create list of order_ids from provided orders
        order_ids = []
        for order_id in orders.keys(): 
            order_ids.append(order_id)
        print("Canceling %d Open Orders..." % len(order_ids))

        # TODO: need to handle partially filled orders here!


        # for each order, cancel it 
        for order_id in order_ids:
            marketMaker.cancel_order(order_id)

        print("✔\tCanceled %d Open Orders\t\t5 points" % len(order_ids))
    except Exception as e: # work on python 3.x
        print("𐄂\tCancel %d Open Orders\t\t0 points", str(e))   

# enter a BUY & a SELL order with a predefined spread around a given mid price
# or last price against the contracts. 
def challengeOrderSet1(marketMaker: marketmarker.MarketMaker) :
    try :
        print("First Buy & Sell Orders...")

        params = marketMaker.generate_order_params(default_quantity=2)

        # excute the buy order 
        buy_token = marketMaker.execute_buy_order(params.buy_request)
        print("\tCreated Buy Order at $%.2f for %d shares, token %s"% (params.buy_request.price, params.buy_request.quantity, buy_token))

        # excute the sell order 
        sell_token = marketMaker.execute_sell_order(params.sell_request)
        print("\tCreated Sell Order at $%.2f for %d shares, token %s"% (params.sell_request.price, params.sell_request.quantity, sell_token))
            
        print("✔\tFirst Buy & Sell Orders\t\t20 points")
    except Exception as e: # work on python 3.x
        print("𐄂\tFirst Buy & Sell Orders\t\t0 points", str(e))   

    return params

# enter a new set of buy & sell orders with different prices based on the changing 
# mid/last price  against the contracts 
def challengeOrderSet2(marketMaker: marketmarker.MarketMaker, cache) :

    try :
        print("Second Buy & Sell Orders...")

        params = marketMaker.generate_order_params()

        # verify buy is different than first
        if cache["set1_buy_request_price"] != params.buy_request.price :
            print("\tBuy price changed from %.2f to %.2f" % (cache["set1_buy_request_price"], params.buy_request.price ))

        # excute the buy order 
        buy_token = marketMaker.execute_buy_order(params.buy_request)
        print("\tBuy Order created at $%.2f for %d shares, token %s"% (params.buy_request.price, params.buy_request.quantity, buy_token))

        # verify sell is different than first
        if cache["set1_sell_request_price"] != params.sell_request.price :
            print("\tSell price changed from %.2f to %.2f" % (cache["set1_sell_request_price"], params.sell_request.price ))

        # excute the sell order 
        sell_token = marketMaker.execute_sell_order(params.sell_request)
        print("\tSell Order created at $%.2f for %d shares, token %s"% (params.sell_request.price, params.sell_request.quantity, sell_token))
        
        print("✔\tSecond Buy & Sell Orders\t\t20 points")
    except Exception as e: # work on python 3.x
        print("𐄂\tSecond Buy & Sell Orders\t\t0 points", str(e))   

# get order book for buy and sell orders 
def challengeBonusPrintOrderBook(marketMaker: marketmarker.MarketMaker) :

    # get order by id and print array of data for order 
    def printOrder(order_id) :
        order = marketMaker.contracts.get_order(order_id)
        print("\t\t", json.dumps(order))

    try :
        print("Print Order Book...")

        # retrieve buy orders in top of book 
        buyOrders, _ = marketMaker.contracts.getOrderBookBuy(marketMaker.teamPair, contracts.ORDER_BOOK_DEPTH_TOP_OF_BOOK)
        print("\tBuy Orders:")
        for order_id in buyOrders :
            printOrder(order_id) 
        
        # retrieve sell orders in top of book 
        sellOrders, _ = marketMaker.contracts.getOrderBookSell(marketMaker.teamPair, contracts.ORDER_BOOK_DEPTH_TOP_OF_BOOK)
        print("\tSell Orders:")
        for order_id in sellOrders :
            printOrder(order_id) 

        print("✔\tPrint Order Book\t\t10 points")
    except Exception as e: # work on python 3.x
        print("𐄂\tPrint Order Book\t\t0 points", str(e))

# cancel all open orders 
def challengeCancelAllOpenOrders(marketMaker: marketmarker.MarketMaker) :

    try :
        print("Cancel All Open Orders...")

        # load all open orders 
        res = marketMaker.api.openOrders(marketMaker.contracts.sender_address, marketMaker.teamPair)

        if len(res['rows']) > 0:
            # generate a list of open orders
            orderIds = [x["id"] for x in res["rows"]]


            # TODO: need to handle partially filled orders here!



            # execute the cancel all
            marketMaker.cancel_all_orders(orderIds)
        
        print("✔\tCanceled All Open Orders\t\t15 points")
    except Exception as e: # work on python 3.x
        print("𐄂\tCancel All Open Orders\t\t0 points", str(e))

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
    init_file = "./init_challenge_par1-v5"
    if os.path.exists(init_file) :
        # Read & print the entire file 
        with open(init_file, 'r') as reader:
            cache = json.loads(reader.read())

        # Get your open orders from RESTAPI at startup. 
        # 20 points
        orders = challengeStartupLoad(marketMaker=marketMaker)
        
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