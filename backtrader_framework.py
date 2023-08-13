import backtrader as bt 
import pandas as pd 
import datetime
import matplotlib.pyplot as py 
import seaborn as sns 

class RSI_MA(bt.Strategy):

    author = 'Kevin Wang'

    params = (
        ('ma_period',200),
        ('rsi',10),
        ('upper',70),
        ('lower',30),
        ('mid',40)
    )

    def log(self,message,dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        print('{} {}'.format(dt.isoformat(),message))
    
    def __init__(self):

        self.dataclose = self.datas[0].close

        self.record = 0
        self.trading_time = 0
        self.executed_price = 0
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.sellprice = None
        self.sellcomm = None

        self.ma200 = bt.indicators.MovingAverageSimple(self.dataclose,period=self.params.ma_period)
        self.rsi = bt.indicators.RSI(self.data,period=self.params.rsi)

        self.long_condition = bt.And(self.dataclose>self.ma200,bt.indicators.CrossOver(self.rsi,self.params.lower))
        self.short_condition = bt.And(self.dataclose<self.ma200,bt.indicators.CrossDown(self.rsi,self.params.upper))
        self.exit_long = bt.indicators.CrossOver(self.rsi,self.params.mid)
        self.exit_short = bt.indicators.CrossDown(self.rsi,self.params.mid)

    def notify_order(self,order):
        self.bar_executed = len(self)
        if order.status in [order.Submitted,order.Accepted]:
            return 
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('buy executed,price: %.2f, Cost: %.2f, comm %.2f, trades %.2f'%(order.executed.price,order.executed.value,order.executed.comm,self.trading_time))
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm 
            
            else:
                self.log('sell executed, price: %.2f, Cost: %.2f, Comm %.2f, trades %.2f' %(order.executed.price,order.executed.value,order.executed.comm,self.trading_time))
                self.sellprice = order.executed.price
                self.sellcomm = order.executed.comm 
            
            self.bar_executed = len(self)
        
        elif order.status in [order.Canceled,order.Margin,order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
        
        self.order = None 

    def notigy_trade(self,trade):
        if not trade.isclosed:
            return 
        
        self.log('operation profit,gross %.2f, net %.2f' %(trade.pnl,trade.pnlcomm))
    
    def next(self):
        
        #self.log(self.rsi[0])
        if self.order:
            return 
        
        #做多
        if not self.position:
            if self.long_condition:
                self.buy()
        
        #做空
        if not self.position:
            if self.short_condition:
                self.sell() 
        
        #多單出場
        if self.getposition().size>0:
            if self.exit_long or len(self)-self.bar_executed>10:
                self.close()
                self.trading_time = self.trading_time + 1
        
        #空單出場
        if self.getposition().size<0:
            if self.exit_short or len(self)-self.bar_executed>10:
                self.close()
                self.trading_time = self.trading_time + 1

if __name__=='__main__':

    cerebro = bt.Cerebro(cheat_on_open=True)
    cerebro.addstrategy(RSI_MA)

    data = bt.feeds.GenericCSVData(
        
        dataname = "C:\\Users\\10830\\Desktop\\比特幣價格資料.csv",
        fromdate = datetime.datetime(2020,1,1),
        todate = datetime.datetime(2023,6,30),

        nullvalue = 0.0,

        dtformat = ('%Y-%m-%d %H:%M:%S'),

        datetime = 0,
        open = 1,
        high = 2,
        low = 3,
        close = 4,
        volume = 5,
        openinterest = -1
    )

    cerebro.adddata(data)
    cerebro.broker.setcommission(0.001)
    cerebro.broker.setcash(100000)
    cerebro.addsizer(bt.sizers.PercentSizer,percents=50)
    cerebro.addanalyzer(bt.analyzers.PyFolio,_name='PyFolio')
    cerebro.addanalyzer(bt.analyzers.AnnualReturn,_name='AnnualReturn')
    cerebro.addanalyzer(bt.analyzers.DrawDown,_name='DrawDown')

    print('Start {}',format(cerebro.broker.getvalue()))
    back = cerebro.run() 
    print('End {}',format(cerebro.broker.getvalue()))
    print("---------------AnnualReturn---------------")
    print(back[0].analyzers.AnnualReturn.get_analysis())
    print("---------------MaxDrawDown---------------")
    print(back[0].analyzers.DrawDown.get_analysis()['max']['drawdown'])

    # quantstats回測報表
    strat = back[0]
    portfolio_stats = strat.analyzers.getbyname('PyFolio')
    returns,positions,transaction,gross_lev = portfolio_stats.get_pf_items()
    print(returns)
    returns.index = returns.index.tz_convert(None)

    import quantstats
    quantstats.reports.full(returns)
    quantstats.reports.html(returns,output='stats.html',title='RSI策略',download_filename='RSI.html')

    print('Done')
