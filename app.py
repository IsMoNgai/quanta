import time, datetime
import queue
import pandas as pd
import numpy as np
import requests
from threading import Thread
from lightweight_charts import Chart
from sklearn.linear_model import LinearRegression

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.client import Contract, Order, ScannerSubscription
from ibapi.tag_value import TagValue

# create a queue for data coming from Interactive Brokers API
data_queue = queue.Queue()

# a list for keeping track of any indicator lines
current_lines = []

# a list for keeping track of slope for SMA
smaSlope = []

# table for slope display
slope_table = None

# initial chart symbol to show
INITIAL_SYMBOL = "TSM"

# settings for live trading vs. paper trading mode
LIVE_TRADING = False
LIVE_TRADING_PORT = 7496
PAPER_TRADING_PORT = 7497
TRADING_PORT = PAPER_TRADING_PORT
if LIVE_TRADING:
    TRADING_PORT = LIVE_TRADING_PORT

# these defaults are fine
DEFAULT_HOST = '127.0.0.1'
DEFAULT_CLIENT_ID = 1

# Client for connecting to Interactive Brokers
class PTLClient(EWrapper, EClient):
     
    def __init__(self, host, port, client_id):
        EClient.__init__(self, self) 
        
        self.connect(host, port, client_id)

        # create a new Thread
        thread = Thread(target=self.run)
        thread.start()


    def error(self, req_id, code, msg):
        if code in [2104, 2106, 2158]:
            print(msg)
        else:
            print('Error {}: {}'.format(code, msg))


    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.order_id = orderId
        print(f"next valid id is {self.order_id}")

    # callback when historical data is received from Interactive Brokers
    def historicalData(self, req_id, bar):
        t = datetime.datetime.fromtimestamp(int(bar.date))

        # creation bar dictionary for each bar received
        data = {
            'date': t,
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': int(bar.volume)
        }

        # Put the data into the queue
        data_queue.put(data)


    # callback when all historical data has been received
    def historicalDataEnd(self, reqId, start, end):
        print(f"end of data {start} {end}")
            
        # we can update the chart once all data has been received
        update_chart()


    # callback to log order status, we can put more behavior here if needed
    def orderStatus(self, order_id, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        print(f"order status {order_id} {status} {filled} {remaining} {avgFillPrice}")    


    # # callback for when a scan finishes
    # def scannerData(self, req_id, rank, details, distance, benchmark, projection, legsStr):
    #     super().scannerData(req_id, rank, details, distance, benchmark, projection, legsStr)
    #     print("got scanner data")
    #     print(details.contract)

    #     data = {
    #         'secType': details.contract.secType,
    #         'secId': details.contract.secId,
    #         'exchange': details.contract.primaryExchange,
    #         'symbol': details.contract.symbol
    #     }

    #     print(data)
        
    #     # Put the data into the queue
    #     data_queue.put(data)


# called by charting library when the
def get_bar_data(symbol, timeframe):
    print(f"getting bar data for {symbol} {timeframe}")

    contract = Contract()
    contract.symbol = symbol
    contract.secType = 'STK'
    contract.exchange = 'SMART'
    contract.currency = 'USD'
    what_to_show = 'TRADES'
    
    #now = datetime.datetime.now().strftime('%Y%m%d %H:%M:%S')
    chart.spinner(True)

    client.reqHistoricalData(
        2, contract, '', '30 D', timeframe, what_to_show, True, 2, False, []
    )

    time.sleep(1)
       
    chart.watermark(symbol)


# handler for the screenshot button
def take_screenshot(key):
    img = chart.screenshot()
    t = time.time()
    with open(f"screenshot-{t}.png", 'wb') as f:
        f.write(img)


# handles when the user uses an order hotkey combination
def place_order(key):
    # get current symbol
    symbol = chart.topbar['symbol'].value

    # build contract object
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "STK"
    contract.currency = "USD"
    contract.exchange = "SMART"
    
    # build order object
    order = Order()
    order.orderType = "MKT"
    order.totalQuantity = 1

    order.eTradeOnly = False
    order.firmQuoteOnly = False
    
    # get next order id
    client.reqIds(-1)
    time.sleep(2)
    
    # set action to buy or sell depending on key pressed
    # shift+O is for a buy order
    if key == 'O':
        print("buy order")
        order.action = "BUY"

    # shift+P for a sell order
    if key == 'P':
        print("sell order")
        order.action = "SELL"

    # place the order
    if client.order_id:
        print("got order id, placing buy order")
        client.placeOrder(client.order_id, contract, order)


# # implement an Interactive Brokers market scanner
# def do_scan(scan_code):
#     scannerSubscription = ScannerSubscription()
#     scannerSubscription.instrument = "STK"
#     scannerSubscription.locationCode = "STK.US.MAJOR"
#     scannerSubscription.scanCode = scan_code

#     tagValues = []
#     tagValues.append(TagValue("optVolumeAbove", "1000"))
#     tagValues.append(TagValue("avgVolumeAbove", "10000"))

#     client.reqScannerSubscription(7002, scannerSubscription, [], tagValues)
#     time.sleep(1)

#     display_scan()

#     client.cancelScannerSubscription(7002)


#  get new bar data when the user enters a different symbol
def on_search(chart, searched_string):
    get_bar_data(searched_string, chart.topbar['timeframe'].value)
    chart.topbar['symbol'].set(searched_string)


# get new bar data when the user changes timeframes
def on_timeframe_selection(chart):
    print("selected timeframe")
    print(chart.topbar['symbol'].value, chart.topbar['timeframe'].value)
    get_bar_data(chart.topbar['symbol'].value, chart.topbar['timeframe'].value)

# callback for when the user changes the position of the horizontal line
def on_horizontal_line_move(chart, line):
    print(f'Horizontal line moved to: {line.price}')


# # called when we want to render scan results
# def display_scan():
#     # function to call when one of the scan results is clicked
#     def on_row_click(row):
#         chart.topbar['symbol'].set(row['symbol'])
#         get_bar_data(row['symbol'], '5 mins')

#     # create a table on the UI, pass callback function for when a row is clicked
#     table = chart.create_table(
#                     width=0.4, 
#                     height=0.5,
#                     headings=('symbol', 'value'),
#                     widths=(0.7, 0.3),
#                     alignments=('left', 'center'),
#                     position='left', func=on_row_click
#                 )

#     # poll queue for any new scan results
#     try:
#         while True:
#             data = data_queue.get_nowait()
#             # create a new row in the table for each scan result
#             table.new_row(data['symbol'], '')
#     except queue.Empty:
#         print("empty queue")
#     finally:
#         print("done")


# called when we want to update what is rendered on the chart 
def update_chart():
    global current_lines
    global smaSlope

    try:
        bars = []
        while True:  # Keep checking the queue for new data
            data = data_queue.get_nowait()
            bars.append(data)
    except queue.Empty:
        print("empty queue")
    finally:
        # once we have received all the data, convert to pandas dataframe
        df = pd.DataFrame(bars)
        print(df)

        # set the data on the chart
        chart.set(df)
        
        if not df.empty:
            # draw a horizontal line at the high
            chart.horizontal_line(df['high'].max(), func=on_horizontal_line_move)

            # if there were any indicator lines on the chart already (eg. SMA), clear them so we can recalculate
            if current_lines:
                for line in current_lines:
                    line.delete()
                current_lines.clear()

            smaSlope = []
            
            current_lines = []

            # calculate any new lines to render
            # create a line with SMA label on the chart

            majorSMA = [5,10,20,60,120,240]

            colors = {
                5: 'blue',
                10: 'yellow',
                20: 'pink',
                60: 'purple',
                120: 'green',
                240: 'red',
            }


            for sma in majorSMA:
                line = chart.create_line(name=f'SMA {sma}', color=colors.get(sma, 'red'))
                
                line.set(pd.DataFrame({
                    'time': df['date'],
                    f'SMA {sma}': df['close'].rolling(window=sma).mean()
                }).dropna())

                sma_df = pd.DataFrame({
                    'time': df['date'],
                    f'SMA {sma}': df['close'].rolling(window=sma).mean()
                }).dropna()
                
                # Calculate slope only if there is enough data
                if not sma_df.empty:
                    smaSlope.append(calculate_slope(sma_df[f'SMA {sma}']))
                
                current_lines.append(line)

            do_slope()

            # once we get the data back, we don't need a spinner anymore
            chart.spinner(False)

def calculate_slope(sma_values):
    # Ensure we have at least two data points
    if len(sma_values) < 2:
        return np.nan
    
    # Get the last two values
    latest_values = sma_values[-2:]
    
    # Calculate the slope as the difference between the two values
    slope = latest_values.iloc[1] - latest_values.iloc[0]
    
    return slope

def do_slope():
    global slope_table
    
    def on_row_click(row):
        chart.topbar['symbol'].set(row['symbol'])
        get_bar_data(row['symbol'], '5 mins')

    majorSMA = [5, 10, 20, 60, 120, 240]

    # Create or update the table
    if slope_table is None:
        slope_table = chart.create_table(
            width=0.2, 
            height=0.5,
            headings=('symbol', 'slope'),
            widths=(0.5, 0.5),
            alignments=('left', 'center'),
            position='left', func=on_row_click
        )
    else:
        # Clear the existing rows
        slope_table.clear()

    smaId = 0
    for sma in majorSMA:
        if len(smaSlope) == len(majorSMA):
            slope_table.new_row(f'SMA {sma}', smaSlope[smaId])
            smaId += 1

if __name__ == '__main__':
    # create a client object
    client = PTLClient(DEFAULT_HOST, TRADING_PORT, DEFAULT_CLIENT_ID)

    # create chart object, specify display settings
    chart = Chart(toolbox=True, width=1000, inner_width=0.6, inner_height=1)

    # hotkey to place a buy order
    chart.hotkey('shift', 'O', place_order)

    # hotkey to place a sell order
    chart.hotkey('shift', 'P', place_order)

    chart.legend(True)
    
    # set up a function to call when searching for symbol
    chart.events.search += on_search

    # set up top bar
    chart.topbar.textbox('symbol', INITIAL_SYMBOL)

    # give ability to switch between timeframes
    chart.topbar.switcher('timeframe', ('5 mins', '15 mins', '1 hour'), default='5 mins', func=on_timeframe_selection)

    # populate initial chart
    get_bar_data(INITIAL_SYMBOL, '5 mins')

    # # run a market scanner
    # do_scan("HOT_BY_VOLUME")

    # create a button for taking a screenshot of the chart
    chart.topbar.button('screenshot', 'Screenshot', func=take_screenshot)

    # create slope for each SMA
    do_slope()

    # show the chart
    chart.show(block=True)