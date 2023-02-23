# Credit Card Transaction Search Examples  

## Contents
1.  [Summary](#summary)
2.  [Features](#features)
3.  [Prerequisites](#prerequisites)
4.  [Installation](#installation)
5.  [Usage](#usage)
6.  [Index](#index)
7.  [Data](#data)
8.  [Search Scenario 1](#scenario1)
9.  [Search Scenario 2](#scenario2)
10.  [Search Scenario 3](#scenario3)
11.  [Search Scenario 4](#scenario4)
12.  [Search Scenario 5](#scenario5)
13.  [Search Scenario 2](#scenario6)
 
## Summary <a name="summary"></a>
This is collection of CLI and Python examples that first load Redis with credit card transaction records and then demonstrate various search and aggregation scenarios on that data.

## Features <a name="features"></a>
- Loads synthetic transaction data into Redis as hash sets
- Implements multiple search and aggregation operations against Redis.  

## Prerequisites <a name="prerequisites"></a>
- Python

## Installation <a name="installation"></a>
1. Clone this repo.

2.  Install Python requirements
```bash
pip install -r requirements.txt
```

## Usage <a name="usage"></a>
```bash
python3 cctxn.py
```

## Index Build <a name="index"></a>
### CLI
```bash
FT.CREATE txnIdx ON HASH PREFIX 1 "txn:" SCHEMA txn_id TAG SORTABLE txn_date TEXT txn_timestamp NUMERIC SORTABLE txn_amt NUMERIC txn_currency TAG expense_category TAG merchant_name TEXT merchant_address TEXT
```
### Python
```python
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
```

## Data <a name="data"></a>
### Sample Transaction Record
```bash
{'acct_id': 6048764759387,
 'card_last_4': '8403',
 'expense_category': 'HEAL',
 'merchant_address': '097\\ Sanchez\\ Islands\\ Apt\\.\\ 393\\\n'
                     'Port\\ Tammy,\\ AS\\ 71671',
 'merchant_name': 'Walmart',
 'txn_amt': 844.58,
 'txn_currency': 'USD',
 'txn_date': '2021\\-10\\-12T01:10:51',
 'txn_id': 2421948924117,
 'txn_timestamp': 1634022651.0}
```

## Search Scenario 1 <a name="scenario1"></a>
### Business Problem
Range query on dates (6/1/2022 - 7/31/2022, first 3 records sorted by txn_id)
### CLI
```bash
FT.SEARCH txnIdx '@txn_timestamp:[1654063200 1659247200]' SORTBY txn_id ASC RETURN 3 acct_id txn_date txn_amt LIMIT 0 3
```
### Python
```python
begin = time.mktime(datetime.date(2022,6,1).timetuple())
end = time.mktime(datetime.date(2022,7,31).timetuple())
query = Query(f'@txn_timestamp:[{begin} {end}]')\
    .sort_by('txn_id', 'ASC')\
    .return_fields('acct_id', 'txn_date', 'txn_amt')\
    .paging(0, 3)
result = client.ft(IDX_NAME).search(query)
pprint(result.docs) 
```
### Results
```bash
[Document {'id': 'txn:104801452768', 'payload': None, 'acct_id': '3855580637385', 'txn_date': '2022\\-06\\-20T00:16:38', 'txn_amt': '527.3'},
 Document {'id': 'txn:1057562256603', 'payload': None, 'acct_id': '8440141859082', 'txn_date': '2022\\-07\\-06T19:39:08', 'txn_amt': '820.81'},
 Document {'id': 'txn:1108039921439', 'payload': None, 'acct_id': '1214588109355', 'txn_date': '2022\\-07\\-13T13:30:17', 'txn_amt': '485.79'}]
```  

## Search Scenario 2 <a name="scenario2"></a>
### Business Problem
Find 5 most recent transactions by date where Merchant = Kroger, sorted by txn date
### CLI
```bash
FT.SEARCH txnIdx @merchant_name:kroger  SORTBY txn_timestamp ASC RETURN 3 txn_date card_last_4 txn_amt LIMIT 0 5
```
### Python
```python
query = Query('@merchant_name:kroger')\
    .sort_by('txn_timestamp', 'ASC')\
    .return_fields('txn_date', 'card_last_4', 'txn_amt')\
    .paging(0,5)
result = client.ft(IDX_NAME).search(query)
pprint(result.docs) 
```
#### Results
```bash
[Document {'id': 'txn:3254125735126', 'payload': None, 'txn_date': '2020\\-02\\-23T23:36:22', 'card_last_4': '5185', 'txn_amt': '108.4'},
 Document {'id': 'txn:315330658921', 'payload': None, 'txn_date': '2020\\-02\\-25T01:41:21', 'card_last_4': '9303', 'txn_amt': '301.16'},
 Document {'id': 'txn:3309978830143', 'payload': None, 'txn_date': '2020\\-02\\-25T16:35:50', 'card_last_4': '1302', 'txn_amt': '612.1'},
 Document {'id': 'txn:5034622706076', 'payload': None, 'txn_date': '2020\\-03\\-02T20:03:45', 'card_last_4': '3967', 'txn_amt': '565.42'},
 Document {'id': 'txn:8477539870510', 'payload': None, 'txn_date': '2020\\-03\\-03T08:51:41', 'card_last_4': '5115', 'txn_amt': '384.68'}]
```  

## Search Scenario 3 <a name="scenario3"></a>
### Business Problem
Aggregate by expense category with count per category, sorted by count
### CLI
```bash
FT.AGGREGATE txnIdx * GROUPBY 1 @expense_category REDUCE COUNT 0 AS count SORTBY 2 @count DESC
```
### Python
```python
request = AggregateRequest('*')\
    .group_by('@expense_category', reducers.count().alias('count'))\
    .sort_by(Desc('@count'))
result = client.ft(IDX_NAME).aggregate(request)
pprint(result.rows)
```
### Results
```bash
[[b'expense_category', b'FOOD', b'count', b'515'],
 [b'expense_category', b'HOME', b'count', b'513'],
 [b'expense_category', b'GASS', b'count', b'511'],
 [b'expense_category', b'MISC', b'count', b'510'],
 [b'expense_category', b'AUTO', b'count', b'504'],
 [b'expense_category', b'HEAL', b'count', b'501'],
 [b'expense_category', b'PERS', b'count', b'499'],
 [b'expense_category', b'GIFT', b'count', b'495'],
 [b'expense_category', b'GROC', b'count', b'479'],
 [b'expense_category', b'TRAV', b'count', b'473']]
```  

## Search Scenario 4 <a name="scenario4"></a>
### Business Problem
Aggregate on a query from a derived value(txn year).  Return number of transactions per year
### CLI
```bash
FT.AGGREGATE txnIdx * LOAD 1 @txn_date apply 'substr(@txn_date,0,4)' AS year GROUPBY 1 @year REDUCE COUNT 0 AS num_transactions SORTBY 2 @year DESC
```
### Python
```python
request = AggregateRequest('*')\
    .load('@txn_date')\
    .apply(year='substr(@txn_date,0,4)')\
    .group_by('@year', reducers.count().alias('num_transactions'))\
    .sort_by(Desc('@year'))
result = client.ft(IDX_NAME).aggregate(request)
pprint(result.rows)
```
### Results
```bash
[[b'year', b'2023', b'num_transactions', b'238'],
 [b'year', b'2022', b'num_transactions', b'1712'],
 [b'year', b'2021', b'num_transactions', b'1655'],
 [b'year', b'2020', b'num_transactions', b'1395']]
```  

## Search Scenario 5 <a name="scenario5"></a>
### Business Problem
For a merchant with name like "walmart", aggregate on address and find top 3 by txn count
### CLI
```bash
FT.AGGREGATE txnIdx '@merchant_name:%walmrt%' GROUPBY 1 @merchant_address REDUCE COUNT 0 as txn_count sortby 2 @txn_count DESC limit 0 3
```
### Python
```python
request = AggregateRequest('@merchant_name:%walmrt%')\
    .group_by('@merchant_address', reducers.count().alias('txn_count'))\
    .sort_by(Desc('@txn_count'))\
    .limit(0,3)
    result = client.ft(IDX_NAME).aggregate(request)
pprint(result.rows)
```
### Results
```bash
[[b'merchant_address',
  b'50840\\ Cook\\ View\\ Apt\\.\\ 055\\\nMillerbury,\\ PW\\ 64864',
  b'txn_count',
  b'1'],
 [b'merchant_address',
  b'13797\\ Franklin\\ Shores\\\nBrandonville,\\ IN\\ 46042',
  b'txn_count',
  b'1'],
 [b'merchant_address',
  b'Unit\\ 7722\\ Box\\ 2524\\\nDPO\\ AE\\ 36572',
  b'txn_count',
  b'1']]
```
## Search Scenario 6 <a name="scenario6"></a>
### Business Problem
Aggregate total spend for categories that had individual tranactions with value >$500 in Dec 2021
### CLI
```bash
FT.AGGREGATE txnIdx '(@txn_date:2021\-12* @txn_currency:{USD} @txn_amt:[(500, inf])' GROUPBY 1 @expense_category REDUCE SUM 1 @txn_amt as total_spend SORTBY 2 @total_spend DESC
```
### Python
```python
request = AggregateRequest('(@txn_date:2021\-12* @txn_currency:{USD} @txn_amt:[(500, inf])')\
    .group_by('@expense_category', reducers.sum('@txn_amt').alias('total_spend'))\
    .sort_by(Desc('@total_spend'))
result = client.ft(IDX_NAME).aggregate(request)
pprint(result.rows)
```
### Results
```bash
[[b'expense_category', b'FOOD', b'total_spend', b'11137.79'],
 [b'expense_category', b'MISC', b'total_spend', b'8551.65'],
 [b'expense_category', b'HEAL', b'total_spend', b'7449.49'],
 [b'expense_category', b'GIFT', b'total_spend', b'6354.79'],
 [b'expense_category', b'AUTO', b'total_spend', b'5981.9'],
 [b'expense_category', b'HOME', b'total_spend', b'4927.18'],
 [b'expense_category', b'GASS', b'total_spend', b'4528.07'],
 [b'expense_category', b'GROC', b'total_spend', b'4288.77'],
 [b'expense_category', b'PERS', b'total_spend', b'3896.34'],
 [b'expense_category', b'TRAV', b'total_spend', b'3600.05']]
```    