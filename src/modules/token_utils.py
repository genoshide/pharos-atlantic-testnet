import random
from decimal import getcontext

getcontext().prec = 50

def _uni_random(min_value, max_value, decimals=2):
    return round(random.uniform(min_value, max_value), decimals)
