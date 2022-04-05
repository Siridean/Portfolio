import lib_Strategies as LS
import pygad
from tqdm import tqdm


def RunInstance(_d:dict):#Ticker:str, Interval:int, nbars:int):
    global Ticker
    global Interval
    global nbars
    Ticker = _d["Ticker"]
    Interval = _d["Interval"]
    nbars = _d["nbars"] if "nbars" in _d else 12500
    num_generations = _d["ngens"] if "ngens" in _d else 1
    sols = _d["sols"] if "sols" in _d else 8

    Loss_lim = range(5, 20)
    ma_lim = range(1,101)
    Rdev_lim = range(1, 501)
    Rma_lim = range(1, 5)
    Price_lim = range(1, 50)
    Overb_lim = range(0,101)
    Overs_lim = range(-100,1)
    Gene_lims = [Loss_lim, Loss_lim, ma_lim, ma_lim, Rdev_lim, Rdev_lim, Rma_lim, Rma_lim, Price_lim, Price_lim, Overb_lim, Overs_lim]
    #Gene_lims = [range(10,11), range(10,11), range(250,251), range(250,251), range(2,3), range(2,3), range(5,6), range(5,6), range(70,71), range(-70,-69)]

    Kstart, Kend, Kopen, Khigh, Klow, Kclose, Kvol =  LS.GetKline(Ticker=Ticker, Interval=Interval, nbars=nbars)

    def Update(instamce, fitness:list, pbar:tqdm):
        pbar.update(1)
        print(round(max(fitness),2), "%", sep="", end='\r')


    def fitness_function(genes, index):

        Strat = LS.Strategy(0.04, 1+(genes[0]/1000), 1-(genes[1]/1000), Kstart, Kend, Kopen, Khigh, Klow, Kclose)
        
        maUp = LS.sma(Kclose, length=genes[2])
        maDown = LS.sma(Kclose, length=genes[3])
        RdevUp = LS.RelativeDeviation(Kclose, genes[4], maUp)
        RdevDown = LS.RelativeDeviation(Kclose, genes[5], maDown)
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
                """Strat.PosSize = -1
                Strat.Data["ResetDown"] = False
                Strat.Entry = _Kclose
                Strat.EntryBar = t
                Strat.TP = CMaDown"""
                if 1 + ((_Kclose - CMaDown)/_Kclose) > Strat.SLDown:
                    _sl = _Kclose * Strat.SLDown
                else: _sl = _Kclose*(1 + ((_Kclose - CMaDown)/_Kclose))
                Strat.OpenTrade(False, _Kclose, t, CMaDown, _sl)
                Strat.Data["ResetDown"] = False
            #Long Entry Conditions
            elif Strat.PosSize==0 and COUp.Data[t] and (RdevUp.Data[t-1] < Oversold) and Strat.Data["ResetUp"] and PriceDiffUp.Data[t] and t>=minbars:
                """Strat.PosSize = 1
                Strat.Data["ResetUp"] = False
                Strat.Entry = _Kclose
                Strat.EntryBar = t
                Strat.TP = CMaUp"""
                if 1 - ((CMaUp - _Kclose)/_Kclose) < Strat.SLUp:
                    _sl = _Kclose * Strat.SLUp
                else: _sl = _Kclose*(1 - ((CMaUp - _Kclose)/_Kclose))
                Strat.OpenTrade(True, _Kclose, t, CMaUp, _sl)
                Strat.Data["ResetUp"] = False
            elif Strat.PosSize < 0:
                Strat.TP = CMaDown
            elif Strat.PosSize > 0:
                Strat.TP = CMaUp

        Strat.run(ApplyStrat, range(len(Kclose.Data)))

        _prof = Strat.TradeTotals["Profit"]
        _pos = 1 if _prof >= 0 else -1
        fitness = _pos*_prof*Strat.Sharpe
        #return fitness
        return _prof
        

    with tqdm(total=num_generations+1, desc="Generations") as pbar:
        GA_Instance = pygad.GA(num_generations=num_generations,
            num_parents_mating = 4,
            fitness_func = fitness_function,
            sol_per_pop = sols,
            num_genes = 12,
            gene_type=int,
            init_range_low = 2,
            init_range_high = 10,
            parent_selection_type = "sss",
            keep_parents = 1,
            crossover_type = "single_point",
            mutation_type = "random",
            mutation_percent_genes = 25,
            gene_space=Gene_lims,
            #on_start=lambda a: pbar.update(-1),
            #on_fitness=lambda a,b: pbar.update(1),
            #on_fitness=lambda a,b: Update(a,b,pbar),
            on_generation=lambda a: pbar.update(1),
            on_stop=lambda a,b: pbar.update(1),
            )

        GA_Instance.run()

    sol, solution_fitness, solution_idx = GA_Instance.best_solution()
    GA_Instance.plot_fitness(title="Iterative Fitness: " + Ticker  + " " + str(Interval))
    return {"Ticker":Ticker, "Interval":Interval, "Fitness":solution_fitness, "Solution":sol}
    
    """sol, solution_fitness, solution_idx = GA_Instance.best_solution()
    print("Solution Parameters:", " |MaUp:", sol[0],
                                " |MaDown:", sol[1],
                                " |PeriodUp:", sol[2],
                                " |PeriodDown:", sol[3],
                                " |Rmaup:", sol[4],
                                " |RmaDown:", sol[5],
                                " |PriceDiffUp:", sol[6]/1000,
                                " |PriceDiffDown:", sol[7]/1000,
                                " |Overbought:", sol[8],
                                " |Oversold:", sol[9],
                                sep="")
    print("Solution Profit: ", round(solution_fitness*100, 2), "%", sep="")"""




























"""
print("Profit:", Strat.TradeTotals["Profit"])
print("Number of Trades Down / Up / Total:", Strat.TradeTotals["NTradesDown"], "/" , Strat.TradeTotals["NTradesUp"], "/", Strat.TradeTotals["NTrades"])
print("Number of winning Trades Down / Up / Total:", Strat.TradeTotals["NWinTradesDown"], "/", Strat.TradeTotals["NWinTradesUp"], "/", Strat.TradeTotals["NWinTrades"])

#Plotting:
fig, ax = pyplot.subplots(3,1, sharex=True)

#Candles
ax[0].plot(Data["Kline"]["close"])
ax[0].plot(Data["Ind"]["maUp"], "-g")
ax[0].plot(Data["Ind"]["maDown"], "-r")
ax[0].set_title("close")

#RdevUp
ax[1].plot(Data["Ind"]["RdevUp"], "-g")
ax[1].plot(Data["Ind"]["RmaUp"], "-r")
ax[1].set_title("RDevUp")

#RdevDown
ax[2].plot(Data["Ind"]["RdevDown"], "-g")
ax[2].plot(Data["Ind"]["RmaDown"], "-r")
ax[2].set_title("RDevDown")

#Trades
for trade in Strat.TradeData:
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

pyplot.show()
"""