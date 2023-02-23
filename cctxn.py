# Maker: Joey Whelan
# File overview:  Generates random credit card transaction records, stores them in Redis as hash sets, and then performs
# various searches and aggregations.

from faker import Faker
from faker.providers import DynamicProvider
from redis import from_url
from redis.commands.search.field import NumericField, TagField, TextField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.commands.search.aggregation import AggregateRequest, Desc
from redis.commands.search import reducers
import random
import time
import datetime
from pprint import pprint
import re

REDIS_URL = 'redis://localhost:6379'
RECORDS = 5000
IDX_NAME='txnIdx'
PREFIX='txn:'

merchants_provider = DynamicProvider(
    provider_name='merchants',
    elements=['Walmart', 'Nordstrom', 'Amazon', 'Exxon', 'Kroger', 'Safeway', 'United Airlines', 'Office Depot', 'Ford', 'Taco Bell']
)
categories_provider = DynamicProvider(
    provider_name='categories',
    elements= ['AUTO', 'FOOD', 'GASS', 'GIFT', 'TRAV', 'GROC', 'HOME', 'PERS', 'HEAL', 'MISC']
)

def build_index(client): 
        try:
             client.ft(IDX_NAME).dropindex()
        except:
             pass
        idx_def = IndexDefinition(index_type=IndexType.HASH, prefix=[PREFIX])
        schema = [  
            TagField('txn_id', sortable=True),
            TextField('txn_date'),
            NumericField('txn_timestamp', sortable=True),
            NumericField('txn_amt'),
            TagField('txn_currency'),
            TagField('expense_category'),
            TextField('merchant_name'),
            TextField('merchant_address')
        ]
        client.ft(IDX_NAME).create_index(schema, definition=idx_def)
        print(f'*** {IDX_NAME} index built ***')

def generate_data(client, count):
    Faker.seed(0)
    random.seed(0)
    fake = Faker()
    fake.add_provider(merchants_provider)
    fake.add_provider(categories_provider)
    
    for i in range(count):
        tdate = fake.date_time_between(start_date='-3y', end_date='now')
        txn_record = {
            'acct_id': int(fake.ean(length=13)),
            'txn_id': int(fake.ean(length=13)),
            'txn_date': re.escape(tdate.isoformat()),
            'txn_timestamp': time.mktime(tdate.timetuple()),
            'card_last_4': fake.credit_card_number()[-4:],
            'txn_amt': round(random.uniform(1, 1000), 2),
            'txn_currency': 'USD',
            'expense_category': fake.categories(),
            'merchant_name': fake.merchants(),
            'merchant_address': re.escape(fake.address())
        }
        client.hset(f'{PREFIX}{txn_record["txn_id"]}', mapping=txn_record)
        if i == 0:
             print(f'\n*** Sample Transaction Record ***')
             pprint(txn_record)
    print(f'\n*** {RECORDS} transactions inserted into Redis as hash sets ***')

def search(client):

    print('\n*** Search Scenario 1:  Range query on dates (6/1/2022 - 7/31/2022, first 3 records sorted by txn_id) ***')
    begin = time.mktime(datetime.date(2022,6,1).timetuple())
    end = time.mktime(datetime.date(2022,7,31).timetuple())
    query = Query(f'@txn_timestamp:[{begin} {end}]')\
        .sort_by('txn_id', 'ASC')\
        .return_fields('acct_id', 'txn_date', 'txn_amt')\
        .paging(0, 3)
    result = client.ft(IDX_NAME).search(query)
    pprint(result.docs) 

    print('\n*** Search Scenario 2: Find 5 most recent transactions by date where Merchant = Kroger, sorted by txn date ***')
    query = Query('@merchant_name:kroger')\
        .sort_by('txn_timestamp', 'ASC')\
        .return_fields('txn_date', 'card_last_4', 'txn_amt')\
        .paging(0,5)
    result = client.ft(IDX_NAME).search(query)
    pprint(result.docs) 

    print('\n*** Search Scenario 3:  Aggregate by expense category with count per category, sorted by count ***')
    request = AggregateRequest('*')\
        .group_by('@expense_category', reducers.count().alias('count'))\
        .sort_by(Desc('@count'))
    result = client.ft(IDX_NAME).aggregate(request)
    pprint(result.rows)

    print('\n*** Search Scenario 4:  Aggregate on a query from a derived value(txn year).  Return number of transactions per year ***')
    request = AggregateRequest('*')\
        .load('@txn_date')\
        .apply(year='substr(@txn_date,0,4)')\
        .group_by('@year', reducers.count().alias('num_transactions'))\
        .sort_by(Desc('@year'))
    result = client.ft(IDX_NAME).aggregate(request)
    pprint(result.rows)

    print('\n*** Search Scenario 5:  For a merchant with name like "walmart", aggregate on address and find top 3 by txn count  ***')
    request = AggregateRequest('@merchant_name:%walmrt%')\
        .group_by('@merchant_address', reducers.count().alias('txn_count'))\
        .sort_by(Desc('@txn_count'))\
        .limit(0,3)
    result = client.ft(IDX_NAME).aggregate(request)
    pprint(result.rows)

    print('\n*** Search Scenario 6:  Aggregate total spend for categories that had individual tranactions with value >$500 in Dec 2021  ***')
    request = AggregateRequest('(@txn_date:2021\-12* @txn_currency:{USD} @txn_amt:[(500, inf])')\
        .group_by('@expense_category', reducers.sum('@txn_amt').alias('total_spend'))\
        .sort_by(Desc('@total_spend'))
    result = client.ft(IDX_NAME).aggregate(request)
    pprint(result.rows)

if __name__ == '__main__':
    client = from_url(REDIS_URL)    
    build_index(client)
    generate_data(client, RECORDS)
    search(client)