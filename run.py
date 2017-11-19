# Copyright 2015 IBM Corp. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import metrics_tracker_client
from flask import Flask, render_template, jsonify, json, url_for, request, redirect, Response, flash, abort
from dotenv import load_dotenv
import requests
import os
import csv
import datetime
import initialize
import investmentportfolio
import portfoliooptimization

print ('Running portfoliooptimization.py')
app = Flask(__name__)

# On Bluemix, get the port number from the environment variable VCAP_APP_PORT
# When running this app on the local machine, default the port to 8080
port = int(os.getenv('VCAP_APP_PORT', 8080))
host='0.0.0.0'

# I couldn't add the services to this instance of the app so VCAP is empty
# do this to workaround for now
if 'VCAP_SERVICES' in os.environ:
    if str(os.environ['VCAP_SERVICES']) == '{}':
        print ('Using a file to populate VCAP_SERVICES')
        with open('VCAP.json') as data_file:
            data = json.load(data_file)
        os.environ['VCAP_SERVICES'] = json.dumps(data)

#======================================RUN LOCAL======================================
# stuff for running locally
if 'RUN_LOCAL' in os.environ:
    print ('Running locally')
    port = int(os.getenv('SERVER_PORT', '5555'))
    host = os.getenv('SERVER_HOST', 'localhost')
    with open('VCAP.json') as data_file:
        data = json.load(data_file)
    os.environ['VCAP_SERVICES'] = json.dumps(data)

#======================================MAIN PAGES======================================
@app.route('/')
def run():

    init()
    return render_template('index.html')

@app.route('/api/init') #refers to web address. when found...
def init():
    '''
    Populates investment portfolio with universe, benchmark(s), and current portfolio(s).
    Also populates variables needed for the drop-downs like what attributes to consider.
    '''
    #configure instrument universe - the total set of instruments to be considered in the analysis.
    instrumentUniverse,iu_holdings = initialize.universe_from_csv()
    res = investmentportfolio.Create_Portfolio(instrumentUniverse)
    #add initial set of holdings to instrument universe
    res = investmentportfolio.Create_Portfolio_Holdings('instrument_universe',iu_holdings)

    #configure benchmark portfolios
    benchmarks = initialize.benchmarks_from_csv()
    for b in benchmarks:
        res = investmentportfolio.Create_Portfolio(b[0])
        #add initial set of holdings to benchmark
        res = investmentportfolio.Create_Portfolio_Holdings(b[0]['name'],b[1])

    #configure initial portfolio
    my_portfolio,mp_holdings  = initialize.portfolio_from_csv()
    res = investmentportfolio.Create_Portfolio(my_portfolio)
    #add initial set of holdings to my portfolio
    res = investmentportfolio.Create_Portfolio_Holdings(my_portfolio['name'],mp_holdings)

    return Response(json.dumps(res), mimetype='application/json')

#Deletes all holdings and portfolios for cleanup
@app.route('/api/reset',methods=['GET'])
def reset_app():
    '''
    Deletes all portfolios and respective holdings that are of type 'user_portfolio', 'benchmark', and 'root' (instrument universe)
    '''
    portfolios = investmentportfolio.Get_Portfolios_by_Selector('type','user_portfolio')['portfolios']
    portfolios += investmentportfolio.Get_Portfolios_by_Selector('type','benchmark')['portfolios']
    portfolios += investmentportfolio.Get_Portfolios_by_Selector('type','root')['portfolios']
    for p in portfolios:
        holdings = investmentportfolio.Get_Portfolio_Holdings(p['name'],False)
        # delete all holdings
        for h in holdings['holdings']:
            timestamp = h['timestamp']
            rev = h['_rev']
            investmentportfolio.Delete_Portfolio_Holdings(p['name'],timestamp,rev)
        investmentportfolio.Delete_Portfolio(p['name'],p['timestamp'],p['_rev'])
    return "Portfolios deleted successfully."

#Helper functions - created routes for debug purposes
@app.route('/user_portfolio_list',methods=['GET'])
def get_user_portfolio_list():
    '''
    Returns the available user portfolio names in the Investment Portfolio service.
    Uses type='user_portfolio' to specify.
    '''
    names = []
    res = investmentportfolio.Get_Portfolios_by_Selector('type','user_portfolio')
    p = json.loads(json.dumps(res))
    try:
        for a in p['portfolios']:
            names.append(a['name'])
        #Gather only unique names, as there's likely history for the benchmarks.
        names = list(set(names))
        return names
    except:
        return names

@app.route('/benchmark_list')
def get_benchmark_list():
    '''
    Returns the available benchmark portfolio names in the Investment Portfolio service.
    Uses type='bechmark' to specify.
    '''
    names = []
    res = investmentportfolio.Get_Portfolios_by_Selector('type','benchmark')
    p = json.loads(json.dumps(res))
    try:
        for b in p['portfolios']:
            names.append(b['name'])
        #Gather only unique names, as there's likely history for the benchmarks.
        names = list(set(names))
        return names
    except:
        return names

@app.route('/parse_universe')
def parse_universe():
    '''
    Extracts the various types of constraints from the instrument universe portfolio holdings data.
    '''
    constraints = {
        'hard_constraints': [],
        'esg_constraints': [],
        'allocation_constraints': []
    }

    #Get instrument universe - look at first holding tags (since they're all the same)
    iu = investmentportfolio.Get_Portfolio_Holdings('instrument_universe')['holdings'][0]['holdings']['holdings']

    #iterate through headers to figure out what types of constraints exist within the data.
    for key,value in iu[0].items():
        try:
            c_type,c_desc = key.split('_')
            #hard constraints start with 'has_'
            if c_type == 'has':
                constraints['hard_constraints'].append({'type':key,'description':'Any company with significant business operations that deal with ' + str(c_desc) + '.'})
            #esg constraints start with 'esg_'
            if c_type == 'esg':
                constraints['esg_constraints'].append({'type':key,'description':'ESG ranking for a given company\'s ' + str(c_desc) + ' score.'})
        except:
            #allocation constraints have no '_'. Here we need to serve up all possible values from the data to populate the UI.
            if key not in ['instrumentId','CUSIP','asset','Price']:
                enumeration = list(set([row[key] for row in iu]))
                constraints['allocation_constraints'].append({'values':enumeration,'type':key,'description':'The ' + str(key) + ' of the security.'})
    return constraints

@app.route('/api/load',methods=['GET'])
def load():
    '''
    Populates investment portfolio with universe, benchmark(s), and current portfolio(s).
    Also populates variables needed for the drop-downs like what attributes to consider.
    '''
    constraints = parse_universe()
    data ={
        'user_portfolios':get_user_portfolio_list(),
        'benchmark_portfolios':get_benchmark_list(),
        'hard_constraints':constraints['hard_constraints'],
        'esg_constraints':constraints['esg_constraints'],
        'allocation_constraints':constraints['allocation_constraints']
    }
    return Response(json.dumps(data, indent=4,sort_keys=True), mimetype='application/json')

@app.route('/api/optimize',methods=['GET','POST'])
def optimize():
    '''
    Runs an optimization calculation from a series of inputs
    1) Grabs instrument universe, user portfolio and benchmark portfolio
    2) Builds input portfolios in correct format
    3) Iterates through constraints and builds 'subportfolios' - groupings required to leverage constraints
    4) Runs the optimization and returns the set of optimal trades.
    '''
    optimization = {
        'portfolios': [],
        'objectives': [],
        'constraints': []
    }

    #retrieve the json from the ajax call
    req = ''
    if request.method == 'POST':
        req = json.loads(request.data)

    else: #for debug, a sample request
        req = {
	        'user_portfolio': {
		        'Type':'existing',
		        'Name':'my_portfolio'
            },
	        'benchmark':'Aggressive',
	        'hard_constraints':['has_tobacco','has_military'],
	        'esg_constraints':[
		        {'type':'esg_sustainability','value':'Average'},
		        {'type':'esg_environmental','value':'High'}
	        ],
	        'allocation_constraints':[
		        {'type':'asset-class','value':'Equity','allocation':.5,'inequality':'equal'},
		        {'type':'asset-class','value':'Corporate Bonds','allocation':.3,'inequality':'less than or equal'},
                {'type':'asset-class','value':'Government Bonds','allocation':.2,'inequality':'equal'}
            ],
            'result_requirements':[
	            {'type':'AllowShortSales','value':False},
		        {'type':'MaximumInvestmentWeight','value':.2}, #note the decimal! It's a percentage
                {'type':'CashInfusion','value':50000}
            ]
        }

    #FETCH PORTFOLIOS====================================================================================================
    #Grab user portfolio
    if req['user_portfolio'] is not None:
        try:
            user_portfolio = investmentportfolio.Get_Portfolio_Holdings(req['user_portfolio']['Name'])['holdings'][0]['holdings']['holdings']
        except:
            user_portfolio = {
                'name': 'user_portfolio',
                'type':'user_portfolio',
                'holdings':[]
            }
    else:
        user_portfolio = {
            'name': 'user_portfolio',
            'type':'user_portfolio',
            'holdings':[]
        }
    #Grab instrument universe holdings (for instrument universe definition and to grab all the meta-data)
    iu = investmentportfolio.Get_Portfolio_Holdings('instrument_universe')['holdings'][0]['holdings']['holdings']
    #Grab benchmark
    benchmark = investmentportfolio.Get_Portfolio_Holdings(req['benchmark'])['holdings'][0]['holdings']['holdings']
    #CONSTRUCT INSTRUMETN UNIVERSE, BENCHMARK and OBJECTIVE===================================================================
    #need to add position units with anything you currently hold
    tradeable_universe = {
        'name': 'Universe',
        'type':'root',
        'holdings':[]
    }
    for asset in iu:
        if req['user_portfolio']['Type'] != 'new':
            holding = [h['quantity'] for h in user_portfolio if h['instrumentId'] == asset['instrumentId']]
            if holding != []:
                tradeable_universe['holdings'].append({'asset':asset['instrumentId'],'quantity':holding[0]})
            else:
                tradeable_universe['holdings'].append({'asset':asset['instrumentId'],'quantity':0})
        else:
            tradeable_universe['holdings'].append({'asset':asset['instrumentId'],'quantity':0})
    optimization['portfolios'].append(tradeable_universe)

    #Construct benchmark portfolios - assumes benchmarks have defined quantities.
    benchmark_portfolio = {
        'name': req['benchmark'],
        'type':'benchmark',
        'holdings':[]
    }
    for b in benchmark:
        benchmark_portfolio['holdings'].append({'asset':b['instrumentId'],'quantity':b['quantity']})
    optimization['portfolios'].append(benchmark_portfolio)

    #Objective function
    optimization['objectives'] = [{
       'sense': 'minimize',
       'measure': 'variance',
       'attribute': 'return',
       'portfolio': 'Universe',
       'TargetPortfolio': req['benchmark'],
       'timestep': 30,
       'description': 'minimize tracking error squared (variance of the difference between Universe portfolio and Benchmark returns) at time 30 days'
    }]

    #HARD CONSTRAINTS====================================================================================================
    #Add sub-portfolio (how the optimization algorithm knows which asset has which property)
    for hc in req['hard_constraints']:
        #initialize the subportfolio
        if hc != None:
            subportfolio = {
                'ParentPortfolio':'Universe',
                'name':hc,
                'type':'subportfolio',
                'holdings':[]
            }
            #filter the instrument universe on things that have this property. This is easy as it's true/false.
            for asset in iu:
                if asset[hc] == 'TRUE':
                    #Figure out if the user currently holds any of the asset as the quantity needs to be adjusted
                    if req['user_portfolio']['Type'] != 'new':
                        q = [row['quantity'] for row in user_portfolio if row['instrumentId']==asset['instrumentId']]
                        if q!=[]:
                            subportfolio['holdings'].append({'asset':asset['instrumentId'],'quantity':q[0]})
                        else:
                            subportfolio['holdings'].append({'asset':asset['instrumentId'],'quantity':0})
                    else:
                        subportfolio['holdings'].append({'asset':asset['instrumentId'],'quantity':0})

            optimization['portfolios'].append(subportfolio)
            #Add constraint to list
            optimization['constraints'].append({
                'attribute':'weight',
                'portfolio':hc,
                'InPortfolio':'Universe',
                'relation':'equal',
                'constant':0.0,
                'description':'Excluding all securities which have the property ' + hc + '.'
            })

    #ESG CONSTRAINTS====================================================================================================
    #Add sub-portfolio (how the optimization algorithm knows which asset has which property)
    #Until we have a live data stream, we're taking a shortcut and making a single grouping and setting it to x%
    for esgc in req['esg_constraints']:
        #initialize the subportfolio
        subportfolio_name = esgc['value'] + '-' + esgc['type']
        subportfolio = {
            'ParentPortfolio':'Universe',
            'name':subportfolio_name,
            'type':'subportfolio',
            'holdings':[]
        }
        #filter the instrument universe on things that have this property. This is easy as it's true/false.
        for asset in iu:
            if asset[esgc['type']] == esgc['value']:
                if req['user_portfolio']['Type'] != 'new':
                    #Figure out if the user currently holds any of the asset as the quantity needs to be adjusted
                    q = [row['quantity'] for row in user_portfolio if row['instrumentId']==asset['instrumentId']]
                    if q!=[]:
                        subportfolio['holdings'].append({'asset':asset['instrumentId'],'quantity':q[0]})
                    else:
                        subportfolio['holdings'].append({'asset':asset['instrumentId'],'quantity':0})
                else:
                    subportfolio['holdings'].append({'asset':asset['instrumentId'],'quantity':0})
        optimization['portfolios'].append(subportfolio)

        #Add constraint to list
        optimization['constraints'].append({
            'attribute':'weight',
            'portfolio':subportfolio_name,
            'InPortfolio':'Universe',
            'relation':'greater-or-equal',
            'constant':0.5,
            'description':'Setting the portfolio to have an average ' + esgc['type'] + ' score of ' + esgc['value']+ '.'
        })

    #ALLOCATION CONSTRAINTS================================================================================================
    #Add sub-portfolio (how the optimization algorithm knows which asset has which property)
    for ac in req['allocation_constraints']:
        #initialize the subportfolio
        subportfolio_name = ac['type'] + '-' + ac['value']
        subportfolio = {
            'ParentPortfolio':'Universe',
            'name':subportfolio_name,
            'type':'subportfolio',
            'holdings':[]
        }
        #filter the instrument universe on things that have this property. This is easy as it's true/false.
        for asset in iu:
            if asset[ac['type']] == ac['value']:
                #Figure out if the user currently holds any of the asset as the quantity needs to be adjusted
                if req['user_portfolio']['Type'] != 'new':
                    q = [row['quantity'] for row in user_portfolio if row['instrumentId']==asset['instrumentId']]
                    if q!=[]:
                        subportfolio['holdings'].append({'asset':asset['instrumentId'],'quantity':q[0]})
                    else:
                        subportfolio['holdings'].append({'asset':asset['instrumentId'],'quantity':0})
                else:
                    subportfolio['holdings'].append({'asset':asset['instrumentId'],'quantity':0})
        optimization['portfolios'].append(subportfolio)

        #Add constraint to list
        optimization['constraints'].append({
            'attribute':'weight',
            'portfolio':subportfolio_name,
            'InPortfolio':'Universe',
            'relation':ac['inequality'],
            'constant':ac['allocation'],
            'description':'Sets the allocation to assets with a[n] ' +  str(ac['type']) + ' of ' + str(ac['value']) + ' to be ' + str(ac['inequality']) + ' to ' + str(ac['allocation']) + '.'
        })
    #RESULT REQUIREMENTS================================================================================================
    rr = req['result_requirements']
    for r in rr:
        #Short Sale Restriction
        if r['type'] == 'AllowShortSales':
            if r['value'] == 'False':
                optimization['constraints'].append({
                    'attribute':'weight',
                    'relation':'greater-or-equal',
                    'members':'Universe',
                    'constant':0,
                    'description':'no short-sales for assets in Universe portfolio'
                })

        #Maximum weight of any one position
        if r['type'] == 'MaximumInvestmentWeight':
            optimization['constraints'].append({
                'attribute':'weight',
                'relation':'less-or-equal',
                'members':'Universe',
                'constant':r['value'],
                'description':'Weight of each asset from the Universe portfolio does not exceed ' + str(r['value']*100) + '%.'
            })

        #Cash infusions
        if r['type'] == 'CashInfusion':
            optimization['constraints'].append({
                'attribute:': 'value',
                'portfolio': 'Universe',
                'cashadjust': float(r['value']),
                'description': 'cash inflow of ' + str(r['value']) +' monetary units to the Universe portfolio'})

    optimized_portfolio = portfoliooptimization.Optimize(optimization)

    #ASSEMBLE PORTFOLIO ATTRIBUTES================================================================================================
    #We tack on attributes from instrument universe for each optimized holding (oh) in the response from the instrument universe (iu)
    try:
        #only instruments involved in the before or after
        optimized_portfolio['Holdings']  = [row for row in optimized_portfolio['Holdings'] if (row['OptimizedQuantity']!=0 or row['Quantity']!=0)]
        for oh in range(0,len(optimized_portfolio['Holdings'])):
            #Name
            optimized_portfolio['Holdings'][oh]['Name'] = [row['asset'] for row in iu if row['instrumentId']==optimized_portfolio['Holdings'][oh]['Asset']][0]
            #Market Price
            optimized_portfolio['Holdings'][oh]['Price'] = [float(row['Price']) for row in iu if row['instrumentId']==optimized_portfolio['Holdings'][oh]['Asset']][0]
            #Aggregate Value
            optimized_portfolio['Holdings'][oh]['Total Value'] = optimized_portfolio['Holdings'][oh]['Price'] * optimized_portfolio['Holdings'][oh]['OptimizedQuantity']

            #hard constraints
            try:
                for x in req['hard_constraints']:
                    optimized_portfolio['Holdings'][oh][x] = [row[x] for row in iu if row['instrumentId']==optimized_portfolio['Holdings'][oh]['Asset']][0]
            except:
                pass

            #esg constraints
            try:
                for x in req['esg_constraints']:
                    optimized_portfolio['Holdings'][oh][x['type']] = [row[x['type']] for row in iu if row['instrumentId']==optimized_portfolio['Holdings'][oh]['Asset']][0]
            except:
                pass

            #allocation constraints
            try:
                for x in req['allocation_constraints']:
                    optimized_portfolio['Holdings'][oh][x['type']] = [row[x['type']] for row in iu if row['instrumentId']==optimized_portfolio['Holdings'][oh]['Asset']][0]
            except:
                pass

        return Response(json.dumps(optimized_portfolio, indent=4,sort_keys=True), mimetype='application/json')
    except:
        return Response(json.dumps(optimized_portfolio), mimetype='application/json')

if __name__ == '__main__':
    metrics_tracker_client.track()
    app.run(host=host, port=port)

