#!/usr/bin/env python
# coding: utf-8

# In[1]:


pip install sec_api


# In[8]:


import requests
import json
import pandas as pd

# 10-Q filing URL of SouthWest Airlines
def quarterly_filings(api_key):
    filing_url = "https://www.sec.gov/ix?doc=/Archives/edgar/data/0000092380/000009238021000101/luv-20210331.htm"

    # XBRL-to-JSON converter API endpoint
    xbrl_converter_api_endpoint = "https://api.sec-api.io/xbrl-to-json"

    final_url = xbrl_converter_api_endpoint + "?htm-url=" + filing_url + "&token=" + api_key

    # make request to the API
    response = requests.get(final_url)

    # load JSON into memory
    xbrl_json = json.loads(response.text)

    return xbrl_json

# convert XBRL-JSON of income statement to pandas dataframe
def get_income_statement(xbrl_json):
    income_statement_store = {}

    # iterate over each US GAAP item in the income statement
    for usGaapItem in xbrl_json['StatementsOfComprehensiveIncome']:
        values = []
        indicies = []

        for fact in xbrl_json['StatementsOfComprehensiveIncome'][usGaapItem]:
            # only consider items without segment. not required for our analysis.
            if 'segment' not in fact:
                index = fact['period']['startDate'] + '-' + fact['period']['endDate']
                # ensure no index duplicates are created
                if index not in indicies:
                    values.append(fact['value'])
                    indicies.append(index)                    

        income_statement_store[usGaapItem] = pd.Series(values, index=indicies) 

    income_statement = pd.DataFrame(income_statement_store)
    # switch columns and rows so that US GAAP items are rows and each column header represents a date range
    return income_statement.T 


# In[9]:


# get your API key at https://sec-api.io
api_key = "6610bd44fd92d67380456637cb039679351c52aa2a86b8df5c6231728f535701"

def vertical_analysis(api_key):
    xbrl_json = quarterly_filings(api_key)
    income_statement = get_income_statement(xbrl_json)
    income_statement = income_statement[:-5]
    income_statement = income_statement.apply(pd.to_numeric)
    vertical_analysis = income_statement.divide(income_statement.iloc[0]/100)
    return vertical_analysis

vertical_analysis(api_key)


# In[ ]:




