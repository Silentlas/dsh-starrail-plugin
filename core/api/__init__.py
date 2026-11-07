"""
米游社API模块
"""
from .client import MhyClient, MhyApiError
from .config import *
from .ds_sign import generate_ds, generate_device_id
