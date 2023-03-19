# -*- coding: utf-8 -*-
"""
Unusual options volume, polygon.io

just a note, this was coded on a Saturday when mkts closed

@author: AdamGetbags
"""

#pip OR conda install
#pip install polygon-api-client

#import modules
from polygon import RESTClient, NoResultsError
from datetime import datetime, date
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay

#api key from config
from polygonAPIkey import polygonAPIkey
# OR just assign your API as a string variable
# polygonAPIkey = 'apiKeyGoesHere'

# create client and authenticate w/ API key // rate limit 5 requests per min
client = RESTClient(polygonAPIkey) # api_key is used

# empty list to store option data
optionDataList = []
# list equity tickers
tickerList = ['AAPL', 'BAC', 'BA']

# for each equity ticker
for i in tickerList:
    
    print('Gathering data for ' + i)
    # request single ticker data // market type under ticker types in docs
    singleSnap = client.get_snapshot_all(market_type='stocks', 
                                         tickers=i)
    
    # close price // there's a couple different ways to do this
    stockClosePrice = singleSnap[0].day.close
    
    # get all options data for individual ticker
    contractData = []
    for c in client.list_options_contracts(underlying_ticker = i,
                                           limit = 1000):
        contractData.append(c)
    # print(contractData)
        
    # request data for first 20 contracts
    for j in contractData[:20]:
        # accessing option data from object  
        optionTicker = j.ticker
        contractType = j.contract_type
        strikePrice = j.strike_price
        
        # request options snapshot
        optionSnapshot = client.get_snapshot_option(
            underlying_asset = i, 
            option_contract = optionTicker
        )
        # get open interest // if no open interest, continue
        openInterest = optionSnapshot.open_interest
        
        if openInterest == 0:
            print('No open interest for ' + optionTicker)
            continue
        
        # get implied volatility  // delta
        impVol = optionSnapshot.implied_volatility
        delta = optionSnapshot.greeks.delta
        
        # expiration date 
        expirationDate = j.expiration_date
        # from string to datetime
        expirationDateDT = datetime.strptime(expirationDate, "%Y-%m-%d")
        # today datetime - not including hour/minute data
        todayDT = datetime.combine(date.today(), datetime.min.time())
        # days to expiration
        dte = (expirationDateDT - todayDT).days
        
        # determine holidays and business days // not sure if this works
        prevBusinessDayTS = todayDT - CustomBusinessDay(
            calendar=USFederalHolidayCalendar()
        )
        # previous business day to use for daily agg request 
        prevBusinessDayStr = prevBusinessDayTS.strftime('%Y-%m-%d')
        
        # request las quote data
        lastQuote = client.get_last_quote(optionTicker)
        
        # bid // ask // mid // last price quotation
        ask = lastQuote.ask_price
        bid = lastQuote.bid_price
        mid = (ask + bid) / 2
        
        # request trades data to get last price, if no trades, continue 
        trades = []
        for c in client.list_trades(optionTicker, limit = 1000):
            trades.append(c)
        # print(trades)
        
        if len(trades) == 0:
            print('No trades data for ' + optionTicker)
            continue
        
        # validating time of last trade
        timeOfLastTrade = pd.to_datetime(trades[0].sip_timestamp)
        lastTradeDate = timeOfLastTrade.strftime('%Y-%m-%d')
        
        # last price 
        lastOptionPrice = trades[0].price
        
        # request daily agg data // if there is no volume, continue
        try: 
            dailyOptionData = client.get_aggs(ticker = optionTicker, 
                                         multiplier = 1,
                                         timespan = 'day',
                                         from_ = prevBusinessDayStr,
                                         to = prevBusinessDayStr)
            
        # if there is no option volume, then continue to next contract
        except NoResultsError:
            print('No daily data for ' + optionTicker)
            continue 
        
        # get volume data 
        volume = dailyOptionData[0].volume
        # get open interest data
        volumeOverOpenInt = volume/openInterest
    
        # write individual option data to list 
        optionDataList.append([i,
                               stockClosePrice,
                               contractType,
                               strikePrice,
                               expirationDate,
                               dte,
                               bid,
                               mid,
                               ask,
                               lastOptionPrice,
                               volume,
                               openInterest,
                               volumeOverOpenInt,
                               impVol,
                               delta,
                               lastTradeDate])
        
        print('Data gathered successfully for ' + optionTicker)

# list to dataframe
unusualOptionData = pd.DataFrame(optionDataList)
unusualOptionData.columns = ['Symbol',
                             'Stock Price',
                             'Type',
                             'Strike',
                             'Exp Date',
                             'DTE',
                             'Bid',
                             'Midpoint',
                             'Ask',
                             'Last',
                             'Volume',
                             'Open Int',
                             'VolOverOpenInt',
                             'IV',
                             'Delta',
                             'Last Trade']

# sort by vol/OI
unusualOptionData = unusualOptionData.sort_values(by=['VolOverOpenInt'],
                                                  ascending=False,
                                                  ignore_index=True)