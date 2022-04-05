import multiprocessing as mp
import GA_Strategy_Optimisation as GA

#Define the tickers and chart intervals you want to optimise.
Tickers = ["SOLUSDT", "BNBUSDT"]
Intervals = [5,15]

def main():
    """The main function that executes a series of genetic optimisations in parallel"""
    #Create function input data as a list of dicts for each Ticker and Interval combination.
    Inputs = [{"Ticker":Ti, "Interval":i, "ngens":50, "sols":8} for Ti in Tickers for i in Intervals]

    #Create a pool for mu;tiprocessing
    pool = mp.Pool(mp.cpu_count()-1)

    #Execute the genetic optimisation of the strategy for the above defined Tickers & Intervals
    Results = pool.map(GA.RunInstance, Inputs)
    
    print(Results)

if __name__ == '__main__':
    main()
