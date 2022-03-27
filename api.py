'''
API endpoints for the Dexalot challenge

Endpoints designed to be called internally 
'''

import requests

class Api :
    
    pairs = None 

    def __init__(self, teamName=None, teamPair=None):
        self.teamName = teamName
        self.teamPair = teamPair

        self.pairs = self.trading_pairs() 

        if teamPair is not None :
            if teamPair not in self.pairs :
                raise Exception("invalid pair name")
            self.teamTradingPair = self.pairs[teamPair]

    def trading_pair(self, pair_name):
        if self.pairs is None :
            self.pairs = self.trading_pairs()

        if pair_name not in self.pairs :
            raise Exception("invalid pair name")   
        return self.pairs[pair_name]     

    # gets list of trading_pairs objects
    def trading_pairs(self):
        '''
        Returns the current pairs.
        [
            {"pair":"TEAM3/AVAX","base":"TEAM3","quote":"AVAX","basedisplaydecimals":1,"quotedisplaydecimals":4,"baseaddress":"0x6806263bC78cF0eC8387909d27397BBc5BE61FfA","quoteaddress":null,"mintrade_amnt":"0.300000000000000000","maxtrade_amnt":"4000.000000000000000000","base_evmdecimals":18,"quote_evmdecimals":18,"auctionmode":0,"auctionendtime":null,"status":"deployed"},
            {"pair":"TEAM4/AVAX","base":"TEAM4","quote":"AVAX","basedisplaydecimals":1,"quotedisplaydecimals":4,"baseaddress":"0x1dc1bCFE5cF9d40Ab05a33901f164Ba651a823f1","quoteaddress":null,"mintrade_amnt":"0.300000000000000000","maxtrade_amnt":"4000.000000000000000000","base_evmdecimals":18,"quote_evmdecimals":18,"auctionmode":0,"auctionendtime":null,"status":"deployed"}
        ]
        '''
        if self.pairs is not None :
            return self.pairs 

        # request all trading pairs 
        res = requests.get('https://api.dexalot-dev.com/api/trading/pairs')
        
        resp = {}
        # generate array of responses for each trading pair 
        for pair in res.json():
            # only include relevant trading pairs
            if self.teamName is not None and pair["pair"].startswith("TEAM") and self.teamName not in pair["pair"] :
                continue
            resp[pair["pair"]] = pair

        return resp
    
    # gets array of open orders given trader address and desired trading pair 
    def openOrders(self, tradeAddress, pair):
        
        # request array of open orders for specific trader address and trading pair 
        resp = requests.get('https://api.dexalot-dev.com/api/trading/openorders/params?traderaddress=%s&pair=%s' % (tradeAddress, pair))
        
        return resp.json()
