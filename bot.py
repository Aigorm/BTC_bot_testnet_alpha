import ccxt
import math
from collections import deque
import time
import datetime
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("API_KEY", "placeholder")
API_SECRET = os.getenv("API_SECRET", "placeholder")

duration = 5*60 #in minutes
interval = 15 #in minutes
optimal_number_of_elements = math.floor(duration/interval)

current_strategy = "buying" #or selling
bought_at = -1 #avrage price of bought tokens
bought_sum = 0 #tokens bought in curret buing session
take_profit = 0.02 #in decimal
buy_deposit = 0.25 #how mutch of our money will be uset to buy
avrage_at = -0.01 #in decimal, we are not doing stop loss
avrage_deposit = 0.10 #how mutch of our money will be uset to avrage our loss
usd = -1 #available USDT
owned = 0 #numbers of tockens owned

sellers_data = deque()
sellers_data_sum = 0
sellers_data_avr = 0
sellers_data_max = 0
spread = 0

exchange = ccxt.binance({'apiKey':API_KEY,
                         'secret':API_SECRET,
                         'options':{'defaultType':'future'}})

exchange.set_sandbox_mode(True)
exchange.fetch_balance()

symbol = 'BTC/USDT'

def get_prices(sym, buy_or_sell = "NONE"):
    try:
        order_book = exchange.fetch_order_book(sym)
        best_bid = order_book['bids'][0][0] if order_book['bids'] else None  # Highest buy offer
        best_ask = order_book['asks'][0][0] if order_book['asks'] else None  # Lowest sell offer

        # print(f"Best Buy (Bid) Price: {best_bid} USDT")
        # print(f"Best Sell (Ask) Price: {best_ask} USDT")

        if buy_or_sell == "buy": # we want to sell
            return best_bid
        elif buy_or_sell == "sell": # we want to buy
            return best_ask
        else:
            print("stary, zwaliles")#PRINTING
    except Exception as e:
        print("Error fetching prices:", str(e))


def analize():
    global sellers_data
    global sellers_data_sum
    global current_strategy
    global bought_at
    global optimal_number_of_elements
    global sellers_data_avr
    global sellers_data_max
    global spread
    global symbol
    
    temp = get_prices(symbol, "sell")
    
    sellers_data.append(temp)
    
    sellers_data_sum += temp



    removed_prev_leader = False
    while len(sellers_data) > optimal_number_of_elements: #adjust the data size
        popped = sellers_data.popleft()
        if popped == sellers_data_max:
            removed_prev_leader = True
        sellers_data_sum -= popped
    sellers_data_avr = sellers_data_sum / len(sellers_data)

    if removed_prev_leader: #find current maximum
        sellers_data_max = max(sellers_data)
    else: 
        sellers_data_max = max(sellers_data_max, temp)

    if current_strategy == "buying":
        spread = (sellers_data_max - temp) / sellers_data_max
    elif current_strategy == "selling":
        spread = (temp - bought_at) / temp
    else:
        print("What went wrong?!?")#PRINTING

def adjust_wallet():
    global usd
    global sellers_data

    balance = exchange.fetch_balance()
    usd = balance['free']['USDT']
    total_usd = balance['free']['USDT'] + balance['free']['BTC'] * sellers_data[-1]

    print(f"Date: {datetime.datetime.now()}, USDT: {balance['free']['USDT']}, BTC: {balance['free']['BTC']}, Total in USD: {total_usd}") #PRINTING

    with open("data_gathered.txt", "a") as f:
        f.write(f"Date: {datetime.datetime.now()}, USDT: {balance['free']['USDT']}, BTC: {balance['free']['BTC']}, Total in USD: {total_usd}\n")
    


def buy():
    global current_strategy
    global bought_at
    global bought_sum
    global buy_deposit
    global usd
    global owned
    global sellers_data
    global symbol

    price_per_pip = sellers_data[-1] * 0.001
    budget = buy_deposit * usd
    quantity = math.floor(budget/price_per_pip)*0.001
    
    if quantity > 0:
        order = exchange.create_order(symbol=symbol,
                                    type='market',
                                    side='buy',
                                    amount=quantity)
        owned += quantity
        bought_sum += quantity * sellers_data[-1]
        bought_at = bought_sum / owned
        current_strategy = "selling"
        print("BUYING at ", sellers_data[-1])#PRINTING
        adjust_wallet()

def try_buy():
    global take_profit
    global spread

    if spread >= take_profit:
        buy()

def avrage():
    global bought_at
    global bought_sum
    global avrage_deposit
    global usd
    global owned
    global sellers_data
    global symbol

    price_per_pip = sellers_data[-1] * 0.001
    budget = avrage_deposit * usd
    quantity = math.floor(budget/price_per_pip)*0.001
    if quantity > 0:
        order = exchange.create_order(symbol=symbol,
                                    type='market',
                                    side='buy',
                                    amount=quantity)
        owned += quantity
        bought_sum += quantity * sellers_data[-1]
        bought_at = bought_sum / owned
        print("AVREGING at ", sellers_data[-1])#PRINTING
        adjust_wallet()
    
def sell():
    global current_strategy
    global bought_at
    global bought_sum
    global owned
    global sellers_data
    global symbol

    quantity = owned
    order = exchange.create_order(symbol=symbol,
                                type='market',
                                side='sell',
                                amount=quantity)
    bought_at = -1
    bought_sum = 0
    owned = 0
    current_strategy = "buying"
    print("selling at ", sellers_data[-1])#PRINTING
    adjust_wallet()

def try_sell():
    global take_profit
    global avrage_at
    global spread

    if spread >= take_profit:
        sell()
    elif spread <= avrage_at:
        avrage()

def innit():
    global current_strategy

    analize()
    adjust_wallet()
    current_strategy = "buying"

    global interval

    try:
        while True:            
            analize()

            if current_strategy == "buying":
                try_buy()
            elif current_strategy == "selling":
                try_sell()
            else:
                print("u fuced up")#PRINTING

            time.sleep(interval*60)
    except KeyboardInterrupt:
        pass

innit()