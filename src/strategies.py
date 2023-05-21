from algosdk.abi import *
from hypothesis import strategies as st


def get_strategy(arg: ABIType):
    if isinstance(arg, UintType):
        return st.integers(
            min_value=0,
            max_value=2**arg.bit_size - 1,
        )
    elif isinstance(arg, UfixedType):
        return st.decimals(
            min_value=0,
            max_value=2**arg.bit_size - 1,
            places=arg.precision
        )
    elif isinstance(arg, BoolType):
        return st.booleans()
    elif isinstance(arg, StringType):
        return st.text()
    elif isinstance(arg, ByteType):
        return st.binary(min_size=0, max_size=4096)
    elif isinstance(arg, ArrayDynamicType):
        item_strat = get_strategy(arg.child_type)
        return st.lists(item_strat)
    elif isinstance(arg, ArrayStaticType):
        item_strat = get_strategy(arg.child_type)
        return st.lists(item_strat, min_size=arg.static_length, max_size=arg.static_length)
    elif isinstance(arg, TupleType):
        item_strats = [get_strategy(item) for item in arg.child_types]
        return st.tuples(*item_strats)
    else:
        return st.text()


def get_method_strategy(method: Method):
    return st.tuples(*[get_strategy(arg.type) for arg in method.args])