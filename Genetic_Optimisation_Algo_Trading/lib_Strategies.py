import statistics
import Kline_Importer
from tqdm import tqdm

def GetKline(Ticker:str, Interval:int, nbars:int):
    """Downloads the kline data for the Ticker and Interval combination, going back nbars"""
    _Kline = Kline_Importer.GetData(Ticker, Interval, nbars)
    
    #Instantiate the Kline data as individual Kline classes for ease of use and performance reasons.
    Kstart = Kline(_Kline["start"])
    Kend = Kline(_Kline["end"])
    Kopen = Kline(_Kline["open"])
    Khigh = Kline(_Kline["high"])
    Klow = Kline(_Kline["low"])
    Kclose = Kline(_Kline["close"])
    Kvol = Kline(_Kline["vol"]) 

    return Kstart, Kend, Kopen, Khigh, Klow, Kclose, Kvol
    

class Kline():
    """Class to store Kline data"""
    def __init__(self, _data:list) -> None:
        self.Data = tuple(_data)

class IndicatorGroup():
    """Class to group custom indicators as subclasses within"""
    instances=[]
    def __init__(self) -> None:
        self.instances.append(self)
        self.Data = [0.0]*12850 #Currently fixed value - needs changing to by changable from Top_Level.py

    def CalcInit(self):
        pass

    
class sma(IndicatorGroup):
    """Simple Moving Average Indicator"""
    def __init__(self, source, length:int = 14) -> None:
        self.src = source
        self.length = length
        self.Calc = self.CalcInit
        super().__init__()

    def CalcInit(self):
        """Check if period is greater than current time. If it is, permanently redirect calls to CalcB (branchless calculation)
        Otherwise, adjust the period to be the same as current time, and calculate a shorter SMA"""
        if t > self.length:
            prd = t #If SMA period has not reach current time, use a smaller period equal to t
        else: 
            #Once period fo SMA is greater than t, change the self.Calc varaible to redirect calls to CalcB.
            #Ensures if statement is only run when necesary (a few times compares to hundreds of million of times.)
            prd = self.length
            self.Calc = self.CalcB

        #Calculate SMA
        self.Data[t] = sum(self.src.Data[t-prd:t+1])/self.length 

    def CalcB(self):
        """Calculate the SMA using it's period"""
        self.Data[t] = sum(self.src.Data[t+1-self.length:t+1])/self.length


class ema(IndicatorGroup):
    """Exponential Moving Average Indicator"""
    def __init__(self, source, length:int = 14, k_factor:int = 2) -> None:
        self.src = source
        self.k = k_factor / (length+1)
        self.length = length
        self.Calc = self.CalcInit
        super().__init__()

    def CalcInit(self):
        """Check if period is equal to current time. Permanently change calls to CalB if so.
        Otherwise, set value to 0.0"""
        if self.length == t:
                sma.CalcB(self)
                self.Calc = self.CalcB
        else: self.Data[t] = 0.0

    def CalcB(self):
        b = self.Data[t-1]
        self.Data[t] = self.k*(self.src.Data[t] - b) + b
        
        

class RelativeDeviation(IndicatorGroup):
    """Relative Deviation Indicator"""
    def __init__(self, _Kclose:Kline, Period:int = 100, ma:sma = None) -> None:
        self.Period = Period
        self.ma = ma
        self.Diffs = [0.0]*len(_Kclose.Data)
        self.Highest = 0.0
        self.Lowest = 0.0
        self.Kclose = _Kclose
        self.Calc = self.CalcInit
        super().__init__()
    
    def CalcInit(self):
        """If period is longer then current time, then do nothing. Otherwise, permanently change calls to CalcB."""
        if self.Period >= t:
            pass
        else:
            self.Calc = self.CalcB
            self.CalcB()

    def CalcB(self):
        """Calculates Relative Deviation"""
        _Kclose = self.Kclose.Data[t]   #Get current close data
        ma = self.ma.Data[t]    #Get current moving average data
        prd = self.Period       #Get period from self
        Sprd = t-prd            #Starting time of period
        
        self.Diffs[t] = _Kclose - ma    #Calculate current difference between closing price and MA

        #Calculate highest and lowest over the period of the indicator
        self.Highest = max(self.Diffs[Sprd+1:t+1])
        self.Lowest = min(self.Diffs[Sprd+1:t+1])

        #Catch presky divide by zero errors which can crop up.
        try:
            Rel = self.Diffs[t]/self.Highest if _Kclose >= ma else -self.Diffs[t]/self.Lowest
        except ZeroDivisionError:
            Rel = 0.0

        #Convert to percantage and update indicator value.
        self.Data[t] = 100*Rel


class CrossOver(IndicatorGroup):
    """Standard Cross-Over Signal"""
    def __init__(self, sourceA, sourceB) -> None:
        self.a = sourceA
        self.b = sourceB
        super().__init__()

    def Calc(self):
        """Check if A has crossed over B (from below to above)"""
        if (self.a.Data[t] > self.b.Data[t]
        and self.a.Data[t-1] <= self.b.Data[t-1]):

            self.Data[t] = True #True if A crossed over B this bar, else False.
        else:
            self.Data[t] = False

class PriceDiff(IndicatorGroup):
    """Price Difference Indicator - Used to ensure there is enough price movement avaiable to overcome fees and spread."""
    def __init__(self, sourceA, sourceB, min:float, DivByA:bool = True) -> None:
        self.a = sourceA
        self.b = sourceB
        self.min = min
        #Early if statement to detemine whether the calculation divides by source A or source B.
        #Ensure is only called at initialisation to avoid hundreds of millions of if statement calls per optimisations.
        if DivByA:
            self.c = sourceA 
            self.Calc = self.CalcA
        else:
            self.c = sourceB
            self.Calc = self.CalcB
        super().__init__()

    def CalcA(self):
        """True if price gap from sourceA to sourceB is greater than min value"""
        ma = self.b.Data[t] + self.b.Data[t-1] - self.b.Data[t-2]
        self.Data[t] = True if (self.a.Data[t] - ma)/self.c.Data[t] > self.min else False
        
    def CalcB(self):
        """True if price gap from sourceA to sourceB is greater than min value"""
        ma = self.a.Data[t] + self.a.Data[t-1] - self.a.Data[t-2]
        self.Data[t] = True if (ma - self.b.Data[t])/self.c.Data[t] > self.min else False


class Strategy:
    """Class defining the Strategy. Controls closing of positions as Takeprofit/Stoploss etc."""
    def __init__(self, commission:float, SLDown:float, SLUp:float, Kstart:Kline, Kend:Kline, Kopen:Kline, Khigh:Kline, Klow:Kline, Kclose:Kline) -> None:
        self.commission = commission
        self.PosSize = 0.0
        self.Data = {}
        self.SLDown = SLDown
        self.SLUp = SLUp
        self.SL = 0.0
        self.TP = 0.0
        self.Entry = 0.0
        self.EntryBar = 0
        self.Kstart = Kstart
        self.Kend = Kend
        self.Kopen = Kopen
        self.Khigh = Khigh
        self.Klow = Klow
        self.Kclose = Kclose
        self.Drawdown = 0.0
        self.MaxDrawdown = 0.0
        self.Sharpe = 0.0

        self.TradeData = [{}]
        self.TradeTotals = {}

        self.TradeData[0]["NTrades"] = 0
        self.TradeData[0]["NTradesDown"] = 0
        self.TradeData[0]["NTradesUp"] = 0
        self.TradeData[0]["NWinTrades"] = 0
        self.TradeData[0]["NWinTradesDown"] = 0
        self.TradeData[0]["NWinTradesUp"] = 0
        self.TradeData[0]["NLoseTrades"] = 0
        self.TradeData[0]["NLoseTradesDown"] = 0
        self.TradeData[0]["NLoseTradesUp"] = 0
        self.TradeData[0]["Entry"] = 0.0
        self.TradeData[0]["Bar"] = 0
        self.TradeData[0]["EBar"] = 0
        self.TradeData[0]["Exit"] = 0.0
        self.TradeData[0]["Profit"] = 0.0

    def OpenTrade(self, long, Entry, t, Limit, Stop):
        """Function to open a trade"""
        self.PosSize = 1 if long else -1
        self.Entry = Entry
        self.EntryBar = t
        self.TP = Limit
        self.SL = Stop


    def CheckTrades(self, t):
        """Fucntion to check whether trades should be closed for profit/loss. Runs each bar."""
        Hi = self.Khigh.Data[t]
        Lo = self.Klow.Data[t]

        if self.PosSize == 0: #If no position open, do nothing.
            return
        elif self.PosSize > 0: #If a long position is open, set lambda functions to be long-based.
            self.Klow.Data[t]
            self.Khigh.Data[t]
            _Lesser = lambda:Lo <= self.SL
            _Greater = lambda: Hi >= self.TP
            _Open = lambda: self.Kopen.Data[t] >= self.TP
            _CloseGreater = True
            _CloseLesser = False
        elif self.PosSize < 0: #If a short position is open, set mabda functions to be short-based.
            _Lesser = lambda: Lo <= self.TP
            _Greater = lambda: Hi >= self.SL
            _Open = lambda: self.Kopen.Data[t] <= self.TP
            _CloseGreater = False
            _CloseLesser = True

        if _Open(): #If bar open cases a take-profit condition, then close trade
            self.TP = self.Kopen.Data[t]
            self.CloseTrade(True)
        elif _Greater() and _Lesser():
            #If order experiences stoploss and takeprofit conditions in the same bar, get 1m data.
            Granular = Kline_Importer.GetGranular("SOLUSDT", self.Kstart.Data[t], self.Kend.Data[t])
            for i in range(len(Granular["close"])):
                Lo = Granular["low"][i]
                Hi = Granular["high"][i]
                if _Greater() and _Lesser():
                    #If 1m data does not resolve conflict. Start sifting through order book data to resolve.
                    _stop = False
                    _start = Granular["start"][i]
                    while not _stop:
                        orders = Kline_Importer.OrderData("SOLUSDT", _start)
                        for order in orders:
                            Hi = Lo = float(order["p"])
                            if _Greater():
                                self.CloseTrade(_CloseGreater)
                                _stop = True
                                break
                            elif _Lesser:
                                self.CloseTrade(_CloseLesser)  
                                _stop = True  
                                break      
                        _start = int(orders[-1]["T"])
                    break
                elif _Greater():
                    self.CloseTrade(_CloseGreater)
                    break
                elif _Lesser():
                    self.CloseTrade(_CloseLesser)
                    break
        elif _Greater():
            self.CloseTrade(_CloseGreater)
        elif _Lesser():
            self.CloseTrade(_CloseLesser)


    def CloseTrade(self, _prof:bool):
        """Close position. Alter strategy profit/loss values based on closing condition."""
        self.TradeData.append({})
        l = len(self.TradeData) - 1
        self.TradeData[l]["Entry"] = self.Entry
        self.TradeData[l]["Bar"] = t-1
        self.TradeData[l]["EBar"] = self.EntryBar

        #Set exit condition based on whether this is a profitable trade closure or not.
        if _prof:
            Ex = self.TP
            self.TradeData[l]["Exit"] = self.TP
        else:
            Ex = self.SL
            self.TradeData[l]["Exit"] = self.SL

        #Calculate profit/loss based on whether a long or short position is open.
        if self.PosSize < 0:
            _profVal = ((self.Entry - Ex)*100/self.Entry) - (2*self.commission)
            _s = "Down"
        elif self.PosSize > 0:
            _profVal = ((Ex - self.Entry)*100/self.Entry) - (2*self.commission)
            _s = "Up"
        else: #Catch any errors due to not having a position open here.
            print("Error - Position Size of Zero at Trade Close!")
            print(self.TradeData)

        #Update strategy values based on outcome of position closure.
        self.TradeData[l]["Profit"] = _profVal
        if _profVal >=0:
            self.Drawdown -= _profVal
            if self.Drawdown < 0:
                self.Drawdown = 0
            self.TradeData[l]["NWinTrades"+_s] = 1
            self.TradeData[l]["NTrades"+_s] = 1
        else:
            self.Drawdown -= _profVal
            self.TradeData[l]["NLoseTrades"+_s] = 1
            self.TradeData[l]["NTrades"+_s] = 1

        

        self.TradeCleanup()


    def TradeCleanup(self):
        """Resest trade values in case they weren't already cleared.
        Update the drawdown values"""
        if self.Drawdown > self.MaxDrawdown:
            self.MaxDrawdown = self.Drawdown
        self.Entry = 0.0
        self.TP = 0.0
        self.SL = 0.0
        self.PosSize = 0

    
    def run(self, ApplyStrat, Datarng:range):
        """Main strategy function. Steps through each bar of data and updates the strategy, indicators and orders accordingly."""
        global t
        for t in tqdm(Datarng, "Solution", leave=False): #For each bar
            for ind in IndicatorGroup.instances: #For each indicator
                ind.Calc()                      #Update indicator
            self.CheckTrades(t)                 #Check trade conditions for closures
            ApplyStrat(t)                       #Apply strategy to determine new stoploss/Takeprofits/trade opens.
        self.PostProcessing()                   #Finally process the data into a usable format for upstream programs.
        


    def PostProcessing(self):
        """Organise final values for reporting out and for use in any fitness functions."""
        for l in self.TradeData:
            for key in l:
                if key in self.TradeTotals:
                    self.TradeTotals[key] += l[key]
                else:
                    self.TradeTotals[key] = l[key]

        self.TradeTotals["NTrades"] = self.TradeTotals["NTradesDown"] + self.TradeTotals["NTradesUp"]
        self.TradeTotals["NWinTrades"] = self.TradeTotals["NWinTradesDown"] + self.TradeTotals["NWinTradesUp"]
        self.TradeTotals["NLoseTrades"] = self.TradeTotals["NLoseTradesDown"] + self.TradeTotals["NLoseTradesUp"]

        if len(self.TradeData) > 2:
            _avg = sum([i["Profit"] for i in self.TradeData])/(len(self.TradeData)-1)
            _Sdev = statistics.stdev([i["Profit"] for i in self.TradeData], _avg)
            self.Sharpe = _avg/_Sdev

        IndicatorGroup.instances = []