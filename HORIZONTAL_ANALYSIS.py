#!/usr/bin/env python
# coding: utf-8

# In[1]:


pip install sec_api


# In[21]:


from sec_api import QueryApi
import time
import requests
import json
import pandas as pd
get_ipython().run_line_magic('matplotlib', 'inline')
import matplotlib.pyplot as plt
import matplotlib.ticker as tick
import numpy as np


api_key = '6610bd44fd92d67380456637cb039679351c52aa2a86b8df5c6231728f535701'

def fetch_10k(api_key):
  
    # get your API key by signing up on https://sec-api.io
    query_api = QueryApi(api_key = api_key)

    # fetch all 10-K filings for SouthWest Airlines
    query = {
        "query": {
            "query_string": {
                "query": "(formType:\"10-K\") AND ticker:LUV"
            }
        },
        "from": "0",
        "size": "3",
        "sort": [{ "filedAt": { "order": "desc" } }]
    }

    query_result = query_api.get_filings(query)
    accession_numbers = []

    # extract accession numbers of each filing
    for filing in query_result['filings']:
        accession_numbers.append(filing['accessionNo'])
    return accession_numbers


# get the XBRL-JSON for a given accession number
def get_xbrl_json(accession_no, retry = 0):

    xbrl_converter_api_endpoint = "https://api.sec-api.io/xbrl-to-json"

    request_url = xbrl_converter_api_endpoint + "?accession-no=" + accession_no + "&token=" + api_key

    # linear backoff should happen in case API fails with "too many requests" error
    try:
      response_tmp = requests.get(request_url)
      xbrl_json = json.loads(response_tmp.text)
    except:
      if retry > 5:
        raise Exception('API error')
      
      # wait 500 milliseconds on error and retry
      time.sleep(0.5) 
      return get_xbrl_json(accession_no, retry + 1)

    return xbrl_json

# convert XBRL-JSON of income statement to pandas dataframe
def get_income_statement(xbrl_json):
    income_statement_store = {}

    # iterate over each US GAAP item in the income statement
    for usGaapItem in xbrl_json['StatementsOfIncome']:
        values = []
        indicies = []

        for fact in xbrl_json['StatementsOfIncome'][usGaapItem]:
            # only consider items without segment. not required for our analysis.
            if 'segment' not in fact:
                index = fact['period']['startDate'] + '-' + fact['period']['endDate']
                # ensure no index duplicates are created
                if index not in indicies:
                    values.append(fact['value'])
                    indicies.append(index)                    

        income_statement_store[usGaapItem] = pd.Series(values, index=indicies) 

    income_statement = pd.DataFrame(income_statement_store)
    # switch columns and rows to US GAAP items: rows and date range: columns 
    return income_statement.T 


# clean income statement.
# drop duplicate columns (= column name ends with "_left"), drop key_0 column, drop columns with +5 NaNs
def clean_income_statement(statement):
    for column in statement:

        # column has more than 5 NaN values
        is_nan_column = statement[column].isna().sum() > 5

        if column.endswith('_left') or column == 'key_0' or is_nan_column:
            statement = statement.drop(column, axis=1)
    
    # rearrange columns so that first column represents first quarter
    sorted_columns = sorted(statement.columns.values)
    
    return statement[sorted_columns]

# merge two income statements into one.
# row indicies of both statements have to be the same
# statement_b represents the most recent statement.
def merge_income_statements(statement_a, statement_b):
    return statement_a.merge(statement_b,
                     how="outer", 
                    #  on=statement_b.index, 
                    right_on=statement_b.index, 
                     left_index=True,
                    #  right_index=True,
                     suffixes=('_left', ''))


def print_income_df(accession_numbers):
    previous_income_statement_set = False
    income_statement_final = None
    income_statements = [x[0] for x in enumerate(accession_numbers)]
    for i,accession_no in enumerate(accession_numbers):
    # for accession_no in accession_numbers: # doesn't work with filings filed before 2017 - indicies not equal
        print(accession_no)
        # get XBRL-JSON of 10-K filing by accession number
        xbrl_json_data = get_xbrl_json(accession_no)

        # convert XBRL-JSON to a pandas dataframe
        income_statement_uncleaned = get_income_statement(xbrl_json_data)

        # clean the income statement
        income_statement_cleaned = clean_income_statement(income_statement_uncleaned)

        income_statements[i] = income_statement_cleaned
        
    result = pd.concat(income_statements, axis=1, join="inner")
    result = result.loc[:,~result.columns.duplicated()].copy()
    return result


# custom y axis formatter
def format_dollars(y, pos=None):
    return int(y/1000000000)

def plot_variables(result):
    
    fig, ax = plt.subplots(1, 1, figsize=(8, 6))

    ax = result.astype(float)                             .loc["NetIncomeLoss"]                             .plot.line()
    ax = result.astype(float)                             .loc["RevenueFromContractWithCustomerExcludingAssessedTax"]                             .plot.line()
    ax.legend(['Net Income(in billions USD)', 'Revenue(in billions USD)'])
    ax.set_title('Quarterly Revenues and Net Income Analysis')

    ax.yaxis.set_major_formatter(tick.FuncFormatter(format_dollars))

    plt.ylabel('$ Billions')

    # show all year date ranges
    plt.xticks(ticks=np.arange(len(result.columns)),
               labels=result.columns)

    # format x axis properly
    fig.autofmt_xdate()

    plt.show()


# In[22]:



def horizontal_analysis(api_key):
accession_numbers = fetch_10k(api_key)
result = print_income_df(accession_numbers)
plot_variables(result)


horizontal_analysis(api_key)


# In[ ]:




