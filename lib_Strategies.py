import statistics
import Kline_Importer
from tqdm import tqdm
from numpy.lib.utils import source

def GetKline(Ticker:str, Interval:int, nbars:int):
    _Kline = Kline_Importer.GetData(Ticker, Interval, nbars)
    
    Kstart = Kline(_Kline["start"])
    Kend = Kline(_Kline["end"])
    Kopen = Kline(_Kline["open"])
    Khigh = Kline(_Kline["high"])
    Klow = Kline(_Kline["low"])
    Kclose = Kline(_Kline["close"])
    Kvol = Kline(_Kline["vol"]) 

    return Kstart, Kend, Kopen, Khigh, Klow, Kclose, Kvol
    

class Kline():
    def __init__(self, _data:list) -> None:
        self.Data = tuple(_data)

class IndicatorGroup():
    instances=[]
    def __init__(self) -> None:
        self.instances.append(self)
        self.Data = [0.0]*12850

    def CalcInit(self):
        pass

    
class sma(IndicatorGroup):
    def __init__(self, source, length:int = 14) -> None:
        self.src = source
        self.length = length
        self.Calc = self.CalcInit
        super().__init__()

    def CalcInit(self):
        if t > self.length:
            prd = t
        else: 
            prd = self.length
            self.Calc = self.CalcB
        self.Data[t] = sum(self.src.Data[t-prd:t+1])/self.length

    def CalcB(self):
        self.Data[t] = sum(self.src.Data[t+1-self.length:t+1])/self.length


class ema(IndicatorGroup):
    def __init__(self, source, length:int = 14, k_factor:int = 2) -> None:
        self.src = source
        self.k = k_factor / (length+1)
        self.length = length
        self.Calc = self.CalcInit
        super().__init__()

    def CalcInit(self):
        if self.length == t:
                sma.CalcB(self)
                self.Calc = self.CalcB
        else: self.Data[t] = 0.0

    def CalcB(self):
        b = self.Data[t-1]
        self.Data[t] = self.k*(self.src.Data[t] - b) + b
        
        

class RelativeDeviation(IndicatorGroup):
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
        if self.Period >= t:
            pass
        else:
            self.Calc = self.CalcB
            self.CalcB()

    def CalcB(self):
        _Kclose = self.Kclose.Data[t]
        ma = self.ma.Data[t] 
        prd = self.Period
        Sprd = t-prd
        
        self.Diffs[t] = _Kclose - ma

        self.Highest = max(self.Diffs[Sprd+1:t+1])
        self.Lowest = min(self.Diffs[Sprd+1:t+1])

        try:
            Rel = self.Diffs[t]/self.Highest if _Kclose >= ma else -self.Diffs[t]/self.Lowest
        except ZeroDivisionError:
            Rel = 0.0

        self.Data[t] = 100*Rel


class CrossOver(IndicatorGroup):
    def __init__(self, sourceA, sourceB) -> None:
        self.a = sourceA
        self.b = sourceB
        super().__init__()

    def Calc(self):
        if (self.a.Data[t] > self.b.Data[t]
        and self.a.Data[t-1] <= self.b.Data[t-1]):

            self.Data[t] = True
        else:
            self.Data[t] = False

class PriceDiff(IndicatorGroup):
    def __init__(self, sourceA, sourceB, min:float, DivByA:bool = True) -> None:
        self.a = sourceA
        self.b = sourceB
        self.min = min
        if DivByA:
            self.c = sourceA 
            self.Calc = self.CalcA
        else:
            self.c = sourceB
            self.Calc = self.CalcB
        super().__init__()

    def CalcA(self):
        ma = self.b.Data[t] + self.b.Data[t-1] - self.b.Data[t-2]
        self.Data[t] = True if (self.a.Data[t] - ma)/self.c.Data[t] > self.min else False
        
    def CalcB(self):
        ma = self.a.Data[t] + self.a.Data[t-1] - self.a.Data[t-2]
        self.Data[t] = True if (ma - self.b.Data[t])/self.c.Data[t] > self.min else False


class Strategy:
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
        self.PosSize = 1 if long else -1
        self.Entry = Entry
        self.EntryBar = t
        self.TP = Limit
        self.SL = Stop


    def CheckTrades(self, t):
        Hi = self.Khigh.Data[t]
        Lo = self.Klow.Data[t]

        if self.PosSize == 0:
            return
        elif self.PosSize > 0:
            self.Klow.Data[t]
            self.Khigh.Data[t]
            _Lesser = lambda:Lo <= self.SL
            _Greater = lambda: Hi >= self.TP
            _Open = lambda: self.Kopen.Data[t] >= self.TP
            _CloseGreater = True
            _CloseLesser = False
        elif self.PosSize < 0:
            _Lesser = lambda: Lo <= self.TP
            _Greater = lambda: Hi >= self.SL
            _Open = lambda: self.Kopen.Data[t] <= self.TP
            _CloseGreater = False
            _CloseLesser = True

        if _Open():
            self.TP = self.Kopen.Data[t]
            self.CloseTrade(True)
        elif _Greater() and _Lesser():
            Granular = Kline_Importer.GetGranular("SOLUSDT", self.Kstart.Data[t], self.Kend.Data[t])
            for i in range(len(Granular["close"])):
                Lo = Granular["low"][i]
                Hi = Granular["high"][i]
                if _Greater() and _Lesser():
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
        self.TradeData.append({})
        l = len(self.TradeData) - 1
        self.TradeData[l]["Entry"] = self.Entry
        self.TradeData[l]["Bar"] = t-1
        self.TradeData[l]["EBar"] = self.EntryBar

        if _prof:
            Ex = self.TP
            self.TradeData[l]["Exit"] = self.TP
        else:
            Ex = self.SL
            self.TradeData[l]["Exit"] = self.SL

        if self.PosSize < 0:
            _profVal = ((self.Entry - Ex)*100/self.Entry) - (2*self.commission)
            _s = "Down"
        elif self.PosSize > 0:
            _profVal = ((Ex - self.Entry)*100/self.Entry) - (2*self.commission)
            _s = "Up"
        else:
            print("Error - Position Size of Zero at Trade Close!")
            print(self.TradeData)

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
        if self.Drawdown > self.MaxDrawdown:
            self.MaxDrawdown = self.Drawdown
        self.Entry = 0.0
        self.TP = 0.0
        self.SL = 0.0
        self.PosSize = 0

    
    def run(self, ApplyStrat, Datarng:range):
        global t
        for t in tqdm(Datarng, "Solution", leave=False):
            for ind in IndicatorGroup.instances:
                ind.Calc()
            self.CheckTrades(t)
            ApplyStrat(t)
        self.PostProcessing()
        


    def PostProcessing(self):
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