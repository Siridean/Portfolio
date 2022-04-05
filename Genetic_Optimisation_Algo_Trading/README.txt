A program that allows the user to quickly recreate a strategy in python using classes of indicators and then genetically optimise its parameters based on a customisable fitness function.

File Breakdown:
-Top Level - used to start the program and allow for quick customisations of a pre-defined strategy wihtout being bogged down with large amounts of code.
-Kline importer - The file used to import trading data from the broker via REST API.
-Lib Strategies - This is where the trading strategy is defined using a class system for the indicators.
-Genetic Optimisation - This is where the fitness function and other genetic optimisation parameters are defined.
