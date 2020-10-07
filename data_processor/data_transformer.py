from dataclasses import dataclass

from data_center import DataCenter
from data_center_coref import CorefDataCenter

@dataclass
class DataTransformer(object):
    orig_data: DataCenter
    coref_data: CorefDataCenter