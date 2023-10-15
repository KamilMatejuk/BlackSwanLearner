import os
import json
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
        response = requests.get(f'http://{url.host}:{url.port}{url.slug}')
        assert response.status_code == 200, f'Failed getting signals {response.json()}'
        df = pd.DataFrame(response.json())
        if data is None: data = df
        else: data = pd.merge(data, df, on='timestamp')
    return data


def run_test(signals: pd.DataFrame, model: URL, starting: float, id: str = None):
    # start model
    if id is None:
        response = requests.get(f'http://{model.host}:{model.port}{model.slug}/init')
        assert response.status_code == 200, f'Failed initializing model {response.json()}'
        id = response.text.strip().replace('"', '')
    # go throught data
    results = []
    value_account = starting
    prev_value_account = starting
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
        reward = 0
        action2 = 0 # -1 sell, +1 buy
        if action == 1: # exchange
            reward += 0.05
            if value_assets > 0:
                # sell
                action2 = -1
                value_account = value_assets * state['price']
                value_assets = 0
                profit = (value_account - prev_value_account) / prev_value_account
                reward += profit
            else:
                # buy
                action2 = 1
                value_assets = value_account / state['price']
                prev_value_account = value_account
                value_account = 0
        overall_value = (value_account + value_assets * state['price']) / starting
        reward += overall_value
        reward *= 100
        results.append({
            'timestamp': signals.at[i, 'timestamp'],
            'action': action2,
            'value_account': value_account,
            'value_assets': value_assets,
            'reward': reward,
        })
        # learn
        next_state = _prepare_state(i + 1)
        payload = { 'id': id, 'state': state, 'action': action, 'next_state': next_state, 'reward': reward }
        response = requests.post(f'http://{model.host}:{model.port}{model.slug}/learn', json=payload)
        assert response.status_code == 200, f'Failed learning {response.json()}'
        loss = float(response.text)
        results[-1]['loss'] = loss

    return id, pd.DataFrame(results)


def get_stats(id: str, signals: pd.DataFrame, results: pd.DataFrame, starting: float):
    data = pd.merge(signals, results, on='timestamp')
    transactions = []
    transaction = {}
    value = float(starting)
    for _, row in data.iterrows():
        if row['action'] == 1:
            transaction['buy_time'] = row['timestamp']
            transaction['buy_price'] = row['price']
        if row['action'] == -1:
            transaction['type'] = 'model'
            transaction['sell_time'] = row['timestamp']
            transaction['sell_price'] = row['price']
            transaction['profit'] = row['value_account'] - value
            transaction['starting'] = starting
            value = row['value_account']
            transactions.append(transaction)
            transaction = {}
    if len(transaction) > 0:
        transaction['type'] = 'automatic closing of open positions at the end of test'
        transaction['sell_time'] = data.at[len(data)-1, 'timestamp']
        transaction['sell_price'] = data.at[len(data)-1, 'price']
        account_value = data.at[len(data)-1, 'value_assets'] * transaction['sell_price']
        transaction['profit'] = account_value - value
        transaction['starting'] = starting
        transactions.append(transaction)
    losses = list(data[['timestamp', 'loss']].T.to_dict().values())
    
    nr = ""
    if os.path.exists(f'data/states_and_results_{id}.csv') or \
       os.path.exists(f'data/transactions_{id}.json'):
        i = 1
        while os.path.exists(f'data/states_and_results_{id}_{i}.csv') or \
              os.path.exists(f'data/transactions_{id}_{i}.json'):
            i += 1
        nr = f"_{i}"

    data.to_csv(f'data/states_and_results_{id}{nr}.csv')
    with open(f'data/transactions_{id}{nr}.json', 'w+') as f:
        json.dump(transactions, f)
    return { 'id': id, 'transactions': transactions, 'losses': losses }
