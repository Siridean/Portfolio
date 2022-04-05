from binance import Client
from binance.enums import HistoricalKlinesType
import time

client = Client()



def GetData(Ticker:str, Interval:int, nbars:int=12750):
    """Download trading data from the broker in the Interval (in minutes) specified."""
    sInterval = str(Interval) + 'm'
    #Get and convert the current time to work out the start time for the API request to go back n bars (nbars).
    StartUTC = int(round(time.time() * 1000)) - GetUTC(Interval, nbars)
    Klines = client.get_historical_klines(Ticker, sInterval, start_str=StartUTC, klines_type=HistoricalKlinesType.FUTURES)
    return Organise(Klines)

def GetGranular(Ticker:str, _start, _end):
    """Gets 1 minute data to try and resolve trading conditions where a position should be closed both a take profit and stop loss on same bar.
    This data may allow reloution of which would have happened first without downloading orderbook data."""
    Klines = client.get_historical_klines(Ticker, '1m', start_str=_start, end_str=_end, klines_type=HistoricalKlinesType.FUTURES)
    return Organise(Klines)


def GetUTC(Interval:int, nbars:int):
    """Converts current time to UTC time in milliseconds."""
    Interval_ms = Interval*60000
    return int(Interval_ms*nbars)


def Organise(Klines):
    """ORganises the downloaded kline data into Start, End, OHLC & volume."""
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
    """Downloads order book data from a start-date to and end-date (if specified).
    This data can be used to resolve a situation where an order should be closed
    for both take-profit and stop-loss conditions and 1m granular data cannot resolve it.
    Note: this uses a large data allowance from the broker and so should not be called frequently."""
    if End == None:
        return client.futures_aggregate_trades(symbol=Ticker, startTime=Start)
    else:
        return client.futures_aggregate_trades(symbol=Ticker, startTime=Start, endTime=End)
