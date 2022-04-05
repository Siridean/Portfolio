from numpy import trunc


Tickers = ["SOLUSDT", "BNBUSDT"]
Intervals = [5,15]

def main():
    Inputs = [{"Ticker":Ti, "Interval":i, "ngens":50, "sols":8} for Ti in Tickers for i in Intervals]

    pool = mp.Pool(mp.cpu_count())
    Results = pool.map(GA.RunInstance, Inputs)
    print(Results)

def test():
    Results = GA.RunInstance({"Ticker":"SOLUSDT", "Interval":15, "ngens":30, "sols":8})
    print(Results)
    Validation(Results["Solution"])

def Validation(genes):
        Kstart, Kend, Kopen, Khigh, Klow, Kclose, Kvol =  LS.GetKline(Ticker="SOLUSDT", Interval=15, nbars=12850)


        Strat = LS.Strategy(0.04, 1+(genes[0]/1000), 1-(genes[1]/1000), Kstart, Kend, Kopen, Khigh, Klow, Kclose)
        
        maUp = LS.sma(Kclose, length=genes[2])
        maDown = LS.sma(Kclose, length=genes[3])
        RdevUp = LS.RelativeDeviation(Kclose, genes[4], maUp)
        RdevDown = LS.RelativeDeviation(Kclose,genes[5], maDown)
        RmaUp = LS.ema(RdevUp, genes[6])
        RmaDown = LS.ema(RdevDown, genes[7])
        COUp = LS.CrossOver(RdevUp, RmaUp)
        CODown = LS.CrossOver(RmaDown, RdevDown)
        PriceDiffUp = LS.PriceDiff(maUp, Kclose, float(genes[8]/1000), False)
        PriceDiffDown = LS.PriceDiff(Kclose, maDown, float(genes[9]/1000), True)
        Overbought = genes[10]
        Oversold = genes[11]

        minbars = 350

        #Initial t==0 conditions:
        Strat.Data["ResetDown"] = True
        Strat.Data["ResetUp"] = True

        def ApplyStrat(t:int):
            _Kclose = Kclose.Data[t]
            _Klow = Klow.Data[t]
            _Khigh = Khigh.Data[t]
            CMaDown = maDown.Data[t] + maDown.Data[t-1] - maDown.Data[t-2]
            CMaUp = maUp.Data[t] + maUp.Data[t-1] - maUp.Data[t-2]

            if _Klow <= CMaDown:
                Strat.Data["ResetDown"] = True
            if _Khigh >= CMaUp:
                Strat.Data["ResetUp"] = True

            #Short Entry Conditions
            if Strat.PosSize==0 and CODown.Data[t] and (RdevDown.Data[t-1] > Overbought) and Strat.Data["ResetDown"] and PriceDiffDown.Data[t] and t>=minbars:
                Strat.PosSize = -1
                Strat.Data["ResetDown"] = False
                Strat.Entry = _Kclose
                Strat.EntryBar = t
                Strat.TP = CMaDown
                if 1 + ((_Kclose - CMaDown)/_Kclose) > Strat.SLDown:
                    Strat.SL = _Kclose * Strat.SLDown
                else: Strat.SL = _Kclose*(1 + ((_Kclose - CMaDown)/_Kclose))
            #Long Entry Conditions
            elif Strat.PosSize==0 and COUp.Data[t] and (RdevUp.Data[t-1] < Oversold) and Strat.Data["ResetUp"] and PriceDiffUp.Data[t] and t>=minbars:
                Strat.PosSize = 1
                Strat.Data["ResetUp"] = False
                Strat.Entry = _Kclose
                Strat.EntryBar = t
                Strat.TP = CMaUp
                if 1 - ((CMaUp - _Kclose)/_Kclose) < Strat.SLUp:
                    Strat.SL = _Kclose * Strat.SLUp
                else: Strat.SL = _Kclose*(1 - ((CMaUp - _Kclose)/_Kclose))
            elif Strat.PosSize < 0:
                Strat.TP = CMaDown
            elif Strat.PosSize > 0:
                Strat.TP = CMaUp

            
        Strat.run(ApplyStrat, range(len(Kclose.Data)))

        Profit = Strat.TradeTotals["Profit"]

        print("Drawdown:", Strat.MaxDrawdown)
        print("Sharpe Ratio:", Strat.Sharpe)

        #Plotting:
        fig, ax = pyplot.subplots(3,1, sharex=True)

        #Candles
        ax[0].plot(Kclose.Data)
        ax[0].plot(maUp.Data, "-g")
        ax[0].plot(maDown.Data, "-r")
        ax[0].set_title("close")

        #RdevUp
        ax[1].plot(RdevUp.Data, "-g")
        ax[1].plot(RmaUp.Data, "-r")
        ax[1].axhline(y=70)
        ax[1].axhline(y=-70)
        ax[1].set_title("RDevUp")

        #RdevDown
        ax[2].plot(RdevDown.Data, "-g")
        ax[2].plot(RmaDown.Data, "-r")
        ax[2].axhline(y=70)
        ax[2].axhline(y=-70)
        ax[2].set_title("RDevDown")

        #Trades
        #print(Strat.TradeData)
        print("Profit: ", round(Strat.TradeTotals["Profit"],2), "%", sep="")
        print("Number of Trades Down / Up / Total:", Strat.TradeTotals["NTradesDown"], "/" , Strat.TradeTotals["NTradesUp"], "/", Strat.TradeTotals["NTrades"])
        print("Number of winning Trades Down / Up / Total:", Strat.TradeTotals["NWinTradesDown"], "/", Strat.TradeTotals["NWinTradesUp"], "/", Strat.TradeTotals["NWinTrades"])
        
        with open('data.csv', 'w') as csvfile:
            fieldnames = ['Direction', 'Profit', 'Entry', 'Exit', 'Start', 'End', 'Bar']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for trade in Strat.TradeData:
                if trade == {}:
                    break
                
                dr = "Down" if "NTradesDown" in trade else "Up"
                try:
                    prf = round(trade["Profit"],2)
                except KeyError:
                    print(trade)
                ent = round(trade["Entry"],3)
                ext = round(trade["Exit"],3)
                bar = trade["EBar"]
                strt = datetime.datetime.fromtimestamp(trunc(float(Kstart.Data[bar])/1000))
                end = datetime.datetime.fromtimestamp(trunc(float(Kend.Data[trade["Bar"]])/1000))
                writer.writerow({'Direction':dr, 'Profit':prf, 'Entry':ent, 'Exit':ext, 'Start':strt, 'End':end, 'Bar':bar})


                xs = trade["EBar"]
                xe = trade["Bar"]
                ys = trade["Entry"]
                ye = trade["Exit"]

                if "NTradesDown" in trade:
                    col = "red"
                    dr = 5
                else: 
                    col="green"
                    dr = -5

                ax[0].annotate("", [xs, ys], xytext=(xs, ys+dr), arrowprops=dict(facecolor=col, shrink=0.05))
                ax[0].annotate("", [xe, ye], xytext=(xe, ye-dr), arrowprops=dict(facecolor=col, shrink=0.05))
            csvfile.close()
        pyplot.show()

def GetUTC(Interval:int, nbars:int):
    Interval_ms = Interval*60
    return int(Interval_ms*nbars)        


if __name__ == '__main__':
    import multiprocessing as mp
    import GA_Strategy_Optimisation as GA
    #main()

    import lib_Strategies as LS
    from matplotlib import pyplot
    import datetime
    import csv
    import Kline_Importer
    #Validation([10, 10, 85, 67, 229, 185, 4, 1, 33, 21, 17, -90])

    test()

    """import cProfile
    from pstats import Stats

    pr = cProfile.Profile()
    pr.enable()

    #Validation([85, 67, 229, 185, 4, 1, 33, 21, 17, -90])
    #test()

    pr.disable()
    stats = Stats(pr)
    stats.sort_stats('tottime').print_stats(30)"""
