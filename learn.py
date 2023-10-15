import requests
import numpy as np
import pandas as pd
from schemas_request import StartRequest, URL


def parse_urls(data: StartRequest):
    for signal in data.signals:
        signal['url'].slug = signal['url'].slug.replace('{asset}', data.asset)
        signal['url'].slug = signal['url'].slug.replace('{interval}', data.interval)
        signal['url'].slug = signal['url'].slug.replace('{start_time}', f'{data.start_time}')
        signal['url'].slug = signal['url'].slug.replace('{end_time}', f'{data.end_time}')
    return data
        
    
def get_signals_for_timerange(signals: list[dict]):
    data = None
    for signal in signals:
        url : URL = signal['url']
        import sys
        sys.stderr.write(f'getting url http://{url.host}:{url.port}{url.slug}')
        response = requests.get(f'http://{url.host}:{url.port}{url.slug}')
        assert response.status_code == 200, f'Failed status {response.json()}'
        df = pd.DataFrame(response.json())
        if data is None: data = df
        else: data = pd.merge(data, df, on='timestamp')
    return data


def run_test(signals: pd.DataFrame, model: URL, starting: float):
    # start model
    response = requests.get(f'http://{model.host}:{model.port}{model.slug}/init')
    assert response.status_code == 200, f'Failed initializing model {response.json()}'
    id = response.text
    # go throught data
    results = []
    value_account = starting
    value_assets = 0

    def _prepare_state(i: int):
        state = signals.iloc[i].to_dict()
        del state['timestamp']
        state['value_percent_in_account'] = value_account / (value_account + value_assets)
        state['value_percent_in_assets'] = value_assets / (value_account + value_assets)
        return state
        
    for i in range(len(signals) - 1):
        state = _prepare_state(i)
        payload = { 'id': id, 'state': state }
        # get action
        response = requests.post(f'http://{model.host}:{model.port}{model.slug}/action', json=payload)
        assert response.status_code == 200, f'Failed getting action {response.json()}'
        action = int(response.text)
        # check result
        fee = False
        if action == 1: # exchange
            fee = True
            if value_assets > 0:
                # sell
                value_account = value_assets * state['price']
                value_assets = 0
            else:
                # buy
                value_assets = value_account / state['price']
                value_account = 0
        results.append({
            'timestamp': signals.at[i, 'timestamp'],
            'action': action,
            'value_account': value_account,
            'value_assets': value_assets,
        })
        # learn
        next_state = _prepare_state(i + 1)
        overall_value = value_account + value_assets * state['price']
        if fee: overall_value *= 0.995
        payload = { 'id': id, 'state': state, 'action': action, 'next_state': next_state, 'reward': overall_value }
        response = requests.post(f'http://{model.host}:{model.port}{model.slug}/learn', json=payload)
        assert response.status_code == 200, f'Failed learning {response.json()}'
        loss = float(response.text)
        results[-1]['loss'] = loss

    return pd.DataFrame(results)


def get_stats(signals: pd.DataFrame, results: pd.DataFrame, starting: float):
    data = pd.merge(signals, results, on='timestamp')
    transactions = []
    transaction = { 'type': 'model' }
    value = float(starting)
    for _, row in data.iterrows():
        if row['action'] == 1:
            transaction['buy_time'] = row['timestamp']
            transaction['buy_price'] = row['price']
        if row['action'] == -1:
            transaction['sell_time'] = row['timestamp']
            transaction['sell_price'] = row['price']
            transaction['profit'] = row['value_account'] - value
            value = row['value_account']
            transactions.append(transaction)
            transaction = { 'type': 'model' }
    if len(transaction) > 0:
        transaction['type'] = 'automatic closing of open positions at the end of test'
        transaction['sell_time'] = data.at[len(data)-1, 'timestamp']
        transaction['sell_price'] = data.at[len(data)-1, 'price']
        account_value = data.at[len(data)-1, 'value_assets'] * transaction['sell_price']
        transaction['profit'] = account_value - value
        transactions.append(transaction)
    losses = data[['timestamp', 'loss']].T.to_dict()
    return { 'transactions': transactions, 'losses': losses }
    