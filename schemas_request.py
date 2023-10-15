import re
import time
from dataclasses import dataclass

@dataclass
class URL:
    host: str
    port: int
    slug: str
    
    def validate(self, name: str):
        assert self.host == "localhost" or \
            re.match(r'[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}', self.host), \
            f'{name} URL host has to be localhost or IP address'
        assert isinstance(self.port, int) and self.port >= 1024 and self.port <= 65_535, \
            f'{name} URL port has to be between 1024 and 65535'            

@dataclass
class StartRequest:
    asset: str
    interval: str
    starting_value: float
    start_time: int
    end_time: int
    model_url: URL
    signals: list[dict]
    
    def validate(self):
        assert len(self.asset) > 0, \
            'Cannot pass empty asset'
        assert self.interval in ['1s', '1m', '1h', '1d'], \
            'Only supported intervals are 1s, 1m, 1h, 1d'
        assert self.starting_value > 0, \
            'Starting account value has to be positive'
        assert self.start_time > 0, \
            'Start time should be after 01.01.1970r'
        assert self.end_time < time.time()*1000, \
            'End time cannot be in the future'
        assert self.start_time < self.end_time, \
            'End time has to be after start time'
        assert len(self.signals) > 0, \
            'Signals for model cannot be empty'
        self.model_url = URL(**self.model_url)
        self.model_url.validate('Model')
        for s in self.signals:
            s['url'] = URL(**s['url'])
            s['url'].validate('Signal')

@dataclass
class ContinueRequest(StartRequest):
    id: str
