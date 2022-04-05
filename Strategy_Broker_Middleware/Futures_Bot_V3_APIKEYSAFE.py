#!/usr/bin/env python3

#Imports
#Import Flask to handle webhook
from io import RawIOBase
from os import close, environ, error
from typing import Dict, List
from flask import Flask, request, Response, abort

#Import requests to send POST/GET requests and json for formatting
#import requests
#import json

#Import threading for getting out of webhook wihtout delaying response
import threading

#Import sys and os to handle basic system functions, such as sys.exit() and os.exit()
import sys
import os

#Import datetime for debugging
from datetime import datetime

#Import time for time/sleep operations
import time

#Import CSV for trade logging and plotting
#import csv
#import logging

#Imports the binance module to interact with the exchange and sets the key API info
from binance.client import Client
from werkzeug.datastructures import ImmutableList


f = open("V3_logfile.log", "a")

class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        self.log = f

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)



    def flush(self):
        self.terminal.flush()
        self.log.flush()
        pass

sys.stdout = Logger()

client = Client(api_key="XXXXXX", api_secret="XXXXXX")

#List of IP Addresses that TV webhooks may originate from
IPList = ["52.89.214.238", "34.212.75.30", "54.218.53.128", "52.32.178.7"]

#Base Parameters that MUST match the values from the TV strategy
Ticker1 = "SOL"
Precision = 2
Ticker2 = "USDT"
Ticker = Ticker1 + Ticker2
TickerF = Ticker1 + Ticker2 + "PERP" #"BNBUSDTPERP"
Interval = 15
Capital_Reserve = 0.10

Margin = 1
client.futures_change_leverage(symbol=Ticker, leverage=Margin)
print("Trading with Leverage: ", Margin, "x", sep="")

Token = "%=^¬)JFaElYJTuZL9;q4b_t!(Q/DkkutWNXT_|.nXYruMZ5j$k8Q.V(`&P~_bbM¬yu/<cE<%|<."




def Validate_Origin(OriginIP: ImmutableList):
    """Validates that the request has come from TradingView via one of the whitelisted IP Addresses"""
    
    count = 0 
    for l in OriginIP:
        count += 1
    if count > 1:
        print("Error!: Request may have been tampered with - more than 1 IP Address detected in request route")
        return False
    
    if OriginIP[0] not in IPList:
        print("Error!: Originating IP does not match list of approved IPs")
        print("Shutting down the program to prevent security breach...")
        return False

    print("Requester's Originating IP:", OriginIP[0], "- OK")
    return True


def Get_TV_Data():
    """Gets the data from the TV webhook and updates the global variables"""
    global TV_Order_Price
    global TV_Time
    global TV_Ticker
    global TV_Interval
    global TV_Order_Type
    global TV_Order_ID
    global TV_Token

    TV_Order_Price = content['Order_Price']
    TV_Time = content['Time_Now']
    TV_Ticker = content['Ticker']
    TV_Interval = content['Interval']
    TV_Order_Type = content['Strategy_Direction']
    TV_Order_ID = content['Order_ID']
    TV_Token = content['Token']


def Verify_TV_Data() -> bool:
    """Checks that the TV strategy parameters match the base parameters of this program"""
    global TV_Order_Type
    print("Verifying Webhook Command...")

    TV_Order_Type = TV_Order_Type.upper()

    if TickerF != TV_Ticker:
        print("ERROR!: Tickers do not match, Python/TV:", TickerF, "/", TV_Ticker)
    if Interval != TV_Interval: 
        print("ERROR!: Intervals do not match, Python/TV:", Interval, "/", TV_Interval)   
    if Token != TV_Token:
        print("Error!: Tokens do not match!")
       
    print("Webhook Command & Token Verified", "Ticker:", TickerF, "// Interval:", Interval)
    print("")
    return True


def Check_Order_Type() -> str:
    """Checks whether the order type is 'open' 'Stop Loss' or 'Take Profit'"""
    if (TV_Order_ID == "SLDown" and TV_Order_Type == "BUY") or (TV_Order_ID == "SLUp" and TV_Order_Type == "SELL"):
        return "Stop Loss"
    elif (TV_Order_ID == "TPDown" and TV_Order_Type == "BUY") or (TV_Order_ID== "TPUp" and TV_Order_Type == "SELL"):
        return "Take Profit"
    elif (TV_Order_ID == "Down" and TV_Order_Type == "SELL") or (TV_Order_ID == "Up" and TV_Order_Type == "BUY"):
        return "open"
    else: 
        print("Error!")
        print("'TV_Order_ID' is not one of the 6 allowed reponses 'SLDown', 'SLUp', 'TPDown', 'TPUp', 'Down', 'Up'")
        print("Or the order type and order ID do not match - e.g 'Up' and 'SELL'")
        Error()


def Get_Position_Size():
    """Retrieves the current position size from Binance Servers"""
    global Position_Size

    print("Getting Position Size...")

    Position_Size = 0
    Position = client.futures_position_information(symbol = Ticker)

    long = 0.0
    short = 0.0
    for D in Position:
        if D['positionSide'] == "LONG":
            long = float(D['positionAmt'])
        elif D['positionSide'] == "SHORT":
            short = float(D['positionAmt'])

    if long != 0 and short != 0:
        Error()
    else: Position_Size += long + short
    print ("Position Size:", Position_Size)
    
    
    
    """Code to get open orders
    open_orders = client.get_open_orders(symbol=Ticker)
    if type(open_orders) == list:
        if not open_orders:
            return
        else:
            for D in open_orders:
                if D["side"] == "SELL":
                    Position_Size -= float(D["origQty"])
                elif D["side"] == "BUY":
                    Position_Size += float(D["origQty"])
                else: Error()
    elif type(open_orders) == dict:
        if open_orders["side"] == "SELL":
            Position_Size -= float(open_orders["origQty"])
        elif open_orders["side"] == "BUY":
            Position_Size += float(open_orders["origQty"])
        else: Error()
    else: Error()
    print("Position Size:", Position_Size)"""


def Close_Open_Position(Loss: bool):
    """Sends a POST request to close all open positions on Binance"""
    global TradeList
    order_placed = False

    Get_Position_Size()
    print("")

    if Position_Size > 0:
        CloseDir = "SELL"
        pos_side = "LONG"
    else:
        CloseDir = "BUY"
        pos_side = "SHORT"

    if Loss == True:
        if Position_Size == 0:
            print("Stop-loss - Position already closed")
            return
        else: 
            close_order = client.futures_create_order(symbol=Ticker, side=CloseDir, positionSide=pos_side, type="MARKET", quantity=abs(Position_Size))
            print("Closing with Order:", close_order)
            query_order = client.futures_get_order(symbol=Ticker, orderId=close_order['orderId'])
            while query_order['status'] != "FILLED":
                query_order = client.futures_get_order(symbol=Ticker, orderId=close_order['orderId'])
                time.sleep(1)
            print("Order Status:", query_order['status'])
            print("Execution Price:", query_order['avgPrice'])
            order_placed = True
    else: 
        if Position_Size == 0:
            print("Take-profit - Position already closed")
        else: 
            close_order = client.futures_create_order(symbol=Ticker, side=CloseDir, positionSide=pos_side, type="MARKET", quantity=abs(Position_Size))
            print("Closing with Order:", close_order)
            query_order = client.futures_get_order(symbol=Ticker, orderId=close_order['orderId'])
            while query_order['status'] != "FILLED":
                query_order = client.futures_get_order(symbol=Ticker, orderId=close_order['orderId'])
                time.sleep(1)
            print("Order Status:", query_order['status'])
            print("Execution Price:", query_order['avgPrice'])
            order_placed = True
    
    #TradeList[3] = query_order['price']
    #wr = csv.writer(TradeLog)
    #wr.writerow(TradeList)
    if order_placed:
        TradeProfit = round(100*(1 - (float(query_order['avgPrice']) * EntryDir / EntryPrice)),2) - 0.08
        print("Tade Profit: ", TradeProfit, "%", sep="")


def Get_Capital_Size():
    """Gets Capital size from Binance and updates Capital_Avail using Capitl_Reserve"""
    global Capital_Avail
    global Capital
    global Qty
    Acc_Balance = client.futures_account_balance(recvWindow=10000)
    count = 0
    for D in Acc_Balance:
        if D['asset'] == Ticker2:
            break
        else: count += 1

    Capital = round(float(Acc_Balance[count]['balance']), 2)
    Capital_Avail = round(Capital * (1 - Capital_Reserve), 2)

    Multiplier = 10**Precision
    QtyTrunc = int(Multiplier*(Capital_Avail/float(TV_Order_Price)))
    Qty = float(QtyTrunc)*Margin/Multiplier


def Open_New_Position():
    """Opens a new position on Binance with Stop Loss and checks they were placed on the exchange"""
    global TradeList
    global EntryPrice
    global EntryDir
    Get_Position_Size()
    print("")

    if Position_Size != 0:
        print("Error opening new order - There is already an order in place")
        Error()
    else:
        #if Confirm_Price() == true:
        if TV_Order_Type == "BUY":
            pos_side = "LONG"
            EntryDir = 1
        else: 
            pos_side = "SHORT"
            EntryDir = -1

        new_order = client.futures_create_order(symbol=Ticker, side=TV_Order_Type, positionSide=pos_side, type="MARKET", quantity=Qty)
        print("New Order:", new_order)

        query_order = client.futures_get_order(symbol=Ticker, orderId=new_order['orderId'])
        while query_order['status'] != "FILLED":
            query_order = client.futures_get_order(symbol=Ticker, orderId=new_order['orderId'])
            time.sleep(1)

        print("Order Status:", query_order['status'])
        print("Execution Price:", query_order['avgPrice'])
        EntryPrice = float(query_order['avgPrice'])

        #open Stop Loss
        #wait 1s
        #Query order

        #TradeList = [datetime.today().strftime("%d-%m-%y"), datetime.now().strftime("%H:%M:%S"), query_order['price'], "", pos_side]


def Confirm_Price() -> bool:
    """Confirms that the Current Binance Price ~= TV_Order_Price
    **TBC if required**"""
    global Current_Price
    Current_Price = float(client.get_symbol_ticker(symbol=Ticker)['price'])
    print("Current Price =", Current_Price)
    if TV_Order_Price*0.9998 < Current_Price < TV_Order_Price*1.0002:
        return True
    else: return False


def Processor():
    """Main procedure called when a valid webhook is recieved"""
    e.wait()

    if Validated == False:
        Error()
    
    oType = Check_Order_Type()
    Get_Capital_Size() #Temp Tester Statement
    print("")
    print("Total Capital:", Capital, "Capital Available:", Capital_Avail)
    print(Ticker1, "Trading Qty:", Qty)
    print("")

    if oType == "Stop Loss":
        print("Confirming StopLoss...")
        Close_Open_Position(True)
    elif oType == "open":
        print("opening new order...")
        Open_New_Position()
    elif oType == "Take Profit":
        print("sending TakeProfit order...")
        Close_Open_Position(False)
    else: 
        print("'oType' is incorrect in 'Processor'")
        Error()
    print("----Command executed Successfully---")
    print("")
    print("")
    print("")
    print("")


def Error():
    """Called when this program loses sync with the TV strategy
    Closes all open orders and shuts down the program"""

    print("Error!")
    Get_Position_Size()
    if Position_Size != 0:
        Close_All_Positions()

    f.flush()
    f.close()
    os._exit(0)


def Close_All_Positions():
    """Closes all open positions on the binance server - will continue attempts until successful"""
    while Position_Size != 0:
        Close_Open_Position(False)
        Get_Position_Size()






app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    global content
    global e
    global Validated
    Validated = False

    e = threading.Event()
    x = threading.Thread(target = Processor)

    if request.method == 'POST' and request.is_json:
        contentlist = request.get_json()
        if type(contentlist) == list:
            content = contentlist[0]
        else: content = contentlist
        print("")
        print("----Webhook Command Recieved----")
        print("Trading with Leverage: ", Margin, "x", sep="")

        Get_TV_Data()

        if Verify_TV_Data() == True and Validate_Origin(request.access_route) == True:
            #print("Time response sent to TV", datetime.now().strftime("%d/%m/%y %H:%M:%S"))
            Validated = True
            x.start()
            e.set()
            return Response(status=200)
        else:        
            #Sync lost between python and TV - Check for open orders then exit.
            #Open_Orders?()
            #Close_Order()
            Validated = False
            abort (400)
    else: 
        Validated = False
        abort (400)

if __name__ == '__main__':
    app.run(debug=False, port=443, ssl_context='adhoc')