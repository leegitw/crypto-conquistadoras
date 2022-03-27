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

    def trading_pairs(self):
        '''
        Returns the current pairs.
        '''
        if self.pairs is not None :
            return self.pairs 

        res = requests.get('https://api.dexalot-dev.com/api/trading/pairs')
        
        resp = {}
        for pair in res.json():
            if self.teamName is not None and pair["pair"].startswith("TEAM") and self.teamName not in pair["pair"] :
                continue
            resp[pair["pair"]] = pair

        return resp
    
    def openOrders(self, tradeAddress, pair):
        res = requests.get('https://api.dexalot-dev.com/api/trading/openorders/params?traderaddress=%s&pair=%s' % (tradeAddress, pair))
        return res.json()
