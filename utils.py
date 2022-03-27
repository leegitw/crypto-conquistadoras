from eth_utils.currency import to_wei, MIN_WEI, MAX_WEI
from eth_utils.types import is_string, is_integer
import decimal

# takes a number and converts it to any other ether unit.
def to_wei(value, unit_number, precision) :
    value = float(value)
    value = ('%%.%df' % (precision-1)) % value

    if is_integer(value) or is_string(value):
        d_value = decimal.Decimal(value=value)
    elif isinstance(value, float):
        d_value = decimal.Decimal(value=str(value))
    elif isinstance(value, decimal.Decimal):
        d_value = value
    else:
        raise TypeError("Unsupported type.  Must be one of integer, float, or string")

    s_number = str(unit_number)
 
    unit_str = "1"
    while len(unit_str) <= unit_number :
        unit_str = unit_str + "0"
    unit_value = decimal.Decimal(unit_str)
    if d_value == decimal.Decimal(0):
        return int(0)

    if d_value < 1 and "." in s_number:
        multiplier = len(s_number) - s_number.index(".") - 1
        d_value = decimal.Decimal(value=value) * 10 ** multiplier
        unit_value /= 10 ** multiplier

    result_value = decimal.Decimal(value=d_value) * unit_value

    if result_value <  MIN_WEI or result_value > MAX_WEI:
        raise ValueError("Resulting wei value must be between 1 and 2**256 - 1")

    return int(round(result_value))

# takes a number of a unit and converts it to float.
def from_wei(value, unit_number, percision) :
    if value == 0:
        return 0

    if value < MIN_WEI or value > MAX_WEI:
        raise ValueError("value must be between 1 and 2**256 - 1")

    unit_str = "1"
    while len(unit_str) <= unit_number :
        unit_str = unit_str + "0"
    unit_value = decimal.Decimal(unit_str)

    d_value = decimal.Decimal(value=value)
    result_value = d_value / unit_value

    # TODO: return decimal.Decimal instead
    return float(result_value)