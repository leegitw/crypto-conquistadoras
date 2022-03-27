'''
Main script for the Dexalot challenge.
'''
#######################################################
# Import here useful libraries
#######################################################

from this import d
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

# this signal handler allows for a graceful shutdown when CTRL+C is pressed
def signal_handler(signum, frame):
    global shutdown
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    shutdown = True

# Get Reference Data from the RESTAPI (contract addresses, pairs, trade increments, min, max trade amount) 
def challengeLoadReferenceData(web3 : contracts.Contracts) :
    web3.load_reference_data()
    
    print("✓\tReference Data\t\t20 points")
   
# deposit Avax and Team3 automatically
def challenge1DespositToken(marketMaker: marketmarker.MarketMaker, despositAmount: int) :
    marketMaker.contracts.deposit_token(marketMaker.contracts.sender_address, marketMaker.nativeSymbolName, despositAmount)
    marketMaker.contracts.deposit_token(marketMaker.contracts.sender_address, marketMaker.teamSymbolName, despositAmount)

    print("✓\tDeposit Tokens Automatically\t\t 5 points")

def challengeStartupLoad(marketMaker: marketmarker.MarketMaker) :

    # get open orders at startup 
    orders = marketMaker.load_open_orders()

    return orders

def challengeCancelOpenOrders(marketMaker: marketmarker.MarketMaker, orders) :
    order_ids = []
    for order_id in orders.keys(): 
        order_ids.append(order_id)

    for order_id in order_ids:
        marketMaker.cancel_order(order_id)

# enter a BUY & a SELL order with a predefined spread around a given mid price or 
# last price against the contracts. 
def challengeOrderSet1(marketMaker: marketmarker.MarketMaker) :
    params = marketMaker.generate_order_params(default_quantity=2)

    # excute the buy order 
    marketMaker.execute_buy_order(params.buy_request)

    # excute the sell order 
    marketMaker.execute_sell_order(params.sell_request)

    return params

# enter a new set of buy & sell orders with different prices based on the changing 
# mid/last price  against the contracts 
def challengeOrderSet2(marketMaker: marketmarker.MarketMaker, cache) :
    params = marketMaker.generate_order_params()
 
    # verify buy is different than first
    if cache["set1_buy_request_price"] != params.buy_request.price :
       print("GREAT: buy price is different")

    # excute the buy order 
    marketMaker.execute_buy_order(params.buy_request)

    # verify sell is different than first
    if cache["set1_sell_request_price"] != params.sell_request.price :
       print("GREAT: sell price is different")

    # excute the sell order 
    marketMaker.execute_sell_order(params.sell_request)

def challengeBonusPrintOrderBook(marketMaker: marketmarker.MarketMaker) :

    def printOrder(order_id) :
        order = marketMaker.contracts.get_order(order_id)
        print(json.dumps(order))

    # 
    buyOrders, _ = marketMaker.contracts.getOrderBookBuy(marketMaker.teamPair, contracts.ORDER_BOOK_DEPTH_TOP_OF_BOOK)
    for order_id in buyOrders :
        printOrder(order_id) 
    
    # 
    sellOrders, _ = marketMaker.contracts.getOrderBookSell(marketMaker.teamPair, contracts.ORDER_BOOK_DEPTH_TOP_OF_BOOK)
    for order_id in sellOrders :
        printOrder(order_id) 

def challengeCancelAllOpenOrders(marketMaker: marketmarker.MarketMaker) :

    # load all open orders 
    res = marketMaker.api.openOrders(marketMaker.contracts.sender_address, marketMaker.teamPair)

    if len(res['rows']) == 0:
        return 
    
    # generate a list of open orders
    orderIds = [x["id"] for x in res["rows"]]

    # execute the cancel all
    marketMaker.cancel_all_orders(orderIds)

# this is the main method containing the actual market making strategy logic
def main():

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
    api_client = api.Api(teamName=team_name, teamPair=team_pair)

    # load the trade pairs
    pairs = api_client.trading_pairs()

    # init a new web3 client for handling the contracts
    web3 = contracts.Contracts(rpc_url, sender_address, private_key, team_pair, pairs)

    # Get Reference Data from the RESTAPI (contract addresses, pairs, trade increments, min, max trade amount) 
    # 20 points 
    challengeLoadReferenceData(web3)

    # init the market marker
    marketMaker = marketmarker.MarketMaker(teamPair=team_pair, contracts=web3, api=api_client)

    # file used to persist if the first have of the challenge has been completed.
    init_file = "./init_challenge_par1-v3"
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
    main()