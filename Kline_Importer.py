from binance import Client
from binance.enums import HistoricalKlinesType
import time

client = Client()



def GetData(Ticker:str, Interval:int, nbars:int=12750):
    sInterval = str(Interval) + 'm'
    StartUTC = int(round(time.time() * 1000)) - GetUTC(Interval, nbars)
    Klines = client.get_historical_klines(Ticker, sInterval, start_str=StartUTC, klines_type=HistoricalKlinesType.FUTURES)
    return Organise(Klines)

def GetGranular(Ticker:str, _start, _end):
    Klines = client.get_historical_klines(Ticker, '1m', start_str=_start, end_str=_end, klines_type=HistoricalKlinesType.FUTURES)
    return Organise(Klines)


def GetUTC(Interval:int, nbars:int):
    Interval_ms = Interval*60000
    return int(Interval_ms*nbars)


def Organise(Klines):
    _Kline = {"start":[], "end":[], "open":[], "high":[], "low":[], "close":[], "vol":[]}
    for l in Klines:
        _Kline["start"].append(int(l[0]))
        _Kline["end"].append(int(l[6]))
        _Kline["open"].append(float(l[1]))
        _Kline["high"].append(float(l[2]))
        _Kline["low"].append(float(l[3]))
        _Kline["close"].append(float(l[4]))
        _Kline["vol"].append(float(l[5]))
    return _Kline

def OrderData(Ticker, Start, End=None):
    if End == None:
        return client.futures_aggregate_trades(symbol=Ticker, startTime=Start)
    else:
        return client.futures_aggregate_trades(symbol=Ticker, startTime=Start, endTime=End)
    #return client.get_aggregate_trades({"symbol":Ticker, "startTime":Start, "endTime":End}) 
    #return client.aggregate_trade_iter(symbol=Ticker, start_str=Start)
