# AlgoTrader
A Library for Algorithmic Trading in Python

AlgoTrader simplifies the process of developing and deploying trading algorithms. The user can write a custom trading algorithm by extending the Algo class, which provides methods for fetching historical stock data, accessing account information, and placing trades. The development process can be informed by AlgoTrader's backtest functionality, which allows the user to test how their algorithm would have performed on a given date range. Once finished, the user can deploy their algorithm (either in "live" or "paper trading" mode) by spinning up a local AlgoTrader server, which runs algorithms and logs metrics on a user-specified schedule. Multiple algorithms can be run concurrently, and individual algorithms can be added, paused, or removed while the server is running.

## Installation
``` bash
git clone https://github.com/Acciorocketships/AlgoTrader
cd AlgoTrader
python3 -m pip install -e .
```

## Example
```python

## Define Strategy ##
class MACDstrategy(Algo):

        # automatically called when the strategy is initialised
	def init(self):
                # set cron schedule (as a dict or list of dicts)
		self.set_schedule({"second": 5, "minute": 30, "hour": 9, "day_of_week": "mon-fri"})

        # automatically called according to the schedule that has been set
	def run(self):
                # get data to compute technical indicators
		hist = self.get_data("SPY", days=50)
                # filter the desired times
		if self.data.timeframe == 'minute':
			hist = hist.at_time(datetime.time(9,30))
                # calculate macd tecnical indicator
		macd = ta.trend.macd_diff(hist, window_slow=26, window_fast=12, window_sign=9)[-1]
                # order logic
		if macd > 0:
			self.order_target_percent("SPY", 1.0) # order such that SPY represents 100% of the portfolio value
		else:
			self.order_target_percent("SPY", 0.0) # order such that SPY represents 0% of the portfolio value
			self.cancel_orders("SPY")
      
      
## Backtest ##
# fetch data for SPY stock from 1 Oct 2018 to 1 Aug 2021
data = AlpacaData(start=datetime.datetime(2018,10,1), end=datetime.datetime(2021,8,1), timeframe='day', symbols=["SPY"])
# init algo and manager, and add algo to manager
backtest_manager = Manager(data)
backtest_algo = MACDstrategy()
backtest_manager.add_algo(backtest_algo)
# start backtest
backtest_manager.backtest(start=datetime.datetime(2019,1,1), end=datetime.datetime(2021,8,1))


## Live Trade ##
# fetch SPY data going back 60 days from today
data = AlpacaData(start=60, timeframe='day', symbols=["SPY"])
# init algo and manager, and add algo to manager
manager = Manager(data)
algo = MACDstrategy()
manager.add_algo(algo)
# start live trading
manager.run()

```

## Backtesting

Backtesting returns a dict with the following metrics:
* [Sharpe](https://www.investopedia.com/terms/s/sharperatio.asp)
* [Sortino](https://www.investopedia.com/terms/s/sortinoratio.asp)
* [Alpha](https://www.investopedia.com/terms/a/alpha.asp)
* [Beta](https://www.investopedia.com/terms/b/beta.asp)
* [Compound Annual Growth Rate](https://www.investopedia.com/terms/c/cagr.asp)
* [Max Drawdown](https://www.investopedia.com/terms/m/maximum-drawdown-mdd.asp)
* [Average Win](https://www.investopedia.com/terms/p/profit_loss_ratio.asp)
* [Average Loss](https://www.investopedia.com/terms/p/profit_loss_ratio.asp)
* [Win Rate](https://www.investopedia.com/terms/w/win-loss-ratio.asp)
* [Total Return](https://www.investopedia.com/terms/t/totalreturn.asp)

It also creates an html tearsheet generated by QuantStats:

![Cumulative Returns](https://github.com/Acciorocketships/AlgoTrader/blob/main/images/cumulativereturns.png)
![Monthly Returns](https://github.com/Acciorocketships/AlgoTrader/blob/main/images/monthlyreturns.png)


## API Reference

### Algo

1. set_schedule
```python
algo.set_schedule([{"second": 5, "minute": 30, "hour": 9, "day_of_week": "mon-fri"}]) # runs at 9:30:05 on mon-fri
```
* Sets the schedule for the algorithm to run. If schedule is a list of multiple dicts, then they are merged into one with an OR operation.

2. set_data_source
```python
algo.set_data_source(AlpacaData(start=10, timeframe='minute', symbols=["SPY"], live=True)) # minute data for SPY starting 10 days ago, with live data updates turned on
```
* Sets the data object to which serves as the source for the get_data method

3. get_data
```python
algo.get_data("SPY", length=100) # the last 100 bars of SPY historical data
```
* Retrieves the prices for the given symbol at the timeframe ('day' or 'minute') specified in the data source.
* Instead of length=x, the user can specify days=x to return the last x trading days of data (useful when using minute data)

4. order
```python
algo.order("SPY", amount=1, limit=-0.001, stop=-0.01) # creates a limit buy order for SPY at a price which is 0.1% lower than the current price, and sets a stoploss of 1%
```
* Buys or sells (depending on if amount is positive or negative) the given stock at the given amount
* If limit is not None, the order becomes a limit order where the value of limit is the fraction higher/lower than the current price.
* If stop is not None, the order becomes a stop order where the value of stop is the fraction higher/lower than the current price. stop=-0.01 is a stoploss of 1%.

5. order_target_percent
```python
algo.order_target_percent("SPY", percent=0.8) # buys or sells SPY so it is 80% of our portfolio
```
* Buys or sells the given stock so that the stock makes up the given fraction of your portfolio.
* stop and limit orders can be specified in the same way as the order method

6. cancel_orders
```python
algo.order_target_percent("SPY") # cancels all orders for SPY
```
* Cancels any outstanding buy or sell orders for the given stock (or all stocks if symbol=None)


### Manager

1. add_algo
```python
manager.add_algo(MACDstrategy()) # adds the MACD algo to the manager
```
* Adds an algorithm to the manager so that it can be backtested or live traded
* If the broker or the data source are not set in the the algo's init, then they are set to the same sources as the manager.

2. remove_algo
```python
manager.add_algo(manager.algos[0]) # removes the MACD algo from the manager
```
* Removes an algorithm from the manager

3. backtest
```python
manager.backtest(datetime.datetime(2020,1,1), end=100) # backtests all algorithms in the manager for 100 days starting from 1 Jan 2020 
```
* Runs a backtest for all of the algorithms in the manager, returns a dict of stats, and saves a tearsheet
* Start and end can both be datetimes, or either one can be an int, which denotes x days before end or after start.

4. run
```python
manager.run(paper=True, log_schedule=[{"minute": "30", "hour": "9", "day_of_week": "mon-fri"}]) # starts paper trading, logging the portfolio value at 9:30 on mon-fri
```
* Starts live trading for all algorithms in the manager
* If paper=True, then it trades on the broker's paper account (not with real money)
