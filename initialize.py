import csv
import datetime

def universe_from_csv():
    """
    Returns instrument universe and associated holdings.
    """
    holdings = {
        'timestamp':'{:%Y-%m-%dT%H:%M:%S.%fZ}'.format(datetime.datetime.now()),
        'holdings':[]
    }
    Instrument_Universe = {
        'timestamp': '{:%Y-%m-%dT%H:%M:%S.%fZ}'.format(datetime.datetime.now()) ,
        'closed':False,
        'data':{'type':'root'},
        'name':'instrument_universe'
    }
    with open('Instrument Universe.csv','r') as i_file:
        reader = csv.reader(i_file,delimiter=',')
        headers = []
        universe = [row for row in reader]
    i_file.close()
    headers = [row for row in universe[0]]
    for row in universe[1:]:
        asset = {}
        for i in range(len(row)):
            asset[headers[i]] = row[i]
        holdings['holdings'].append(asset)
    Instrument_Universe['holdings'] = holdings['holdings']
    return Instrument_Universe, holdings

def portfolio_from_csv():
    """
    Returns a current portfolio and associated holdings
    """
    holdings = {
        'timestamp':'{:%Y-%m-%dT%H:%M:%S.%fZ}'.format(datetime.datetime.now()),
        'holdings':[]
    }
    with open('portfolio.csv','r') as p_file:
        reader = csv.reader(p_file,delimiter=',')
        portfolio = [row for row in reader]
    p_file.close()
    headers = [row for row in portfolio[0]]

    my_portfolio = {
        "timestamp": '{:%Y-%m-%dT%H:%M:%S.%fZ}'.format(datetime.datetime.now()) ,
        'closed':False,
        'data':{'type':'user_portfolio'},
        'name':'my_portfolio'
    }

    for p in portfolio[1:]:
        if float(p[2]) > 0:
            asset = {}
            asset[headers[0]] = p[0]
            asset[headers[1]] = p[1]
            asset['quantity'] = float(p[2])
            holdings['holdings'].append(asset)

    return my_portfolio, holdings

def benchmarks_from_csv():
    """
    Returns a set of benchmark portfolios and associated holdings.
    """
    benchmark_portfolios = []
    with open('benchmarks.csv','r') as b_file:
        reader = csv.reader(b_file,delimiter=',')
        benchmarks = [row for row in reader]
    b_file.close()
    headers = [row for row in benchmarks[0]]

    #b is for benchmark
    for b in range(2,len(headers)): #instrument_id, and name
        benchmark = {
            "timestamp": '{:%Y-%m-%dT%H:%M:%S.%fZ}'.format(datetime.datetime.now()),
            'data':{'type':'benchmark'},
            'closed':False,
            "name":headers[b]
        }
        holdings = {
            'timestamp':'{:%Y-%m-%dT%H:%M:%S.%fZ}'.format(datetime.datetime.now()),
            'holdings' :[]
        }
        #a is for asset
        for a in benchmarks[1:]:
            if float(a[b]) > 0:
                asset = {}
                asset[headers[0]] = a[0]
                asset[headers[1]] = a[1]
                asset['quantity'] = float(a[b])
                holdings['holdings'].append(asset)
        benchmark_portfolios.append([benchmark, holdings])

    return benchmark_portfolios
