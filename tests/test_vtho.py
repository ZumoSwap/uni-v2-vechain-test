# Test the generation of VTHO of different type of pools
# Test the share of VTHO of different users
# Test the withdraw of VTHO of different users

import pytest
from .helpers import (
    helper_deploy,
    helper_call,
    helper_transact,
    helper_wait_for_block
)
from .fixtures import (
    solo_connector as connector,
    solo_wallet as wallet,
    clean_wallet,
    router02_contract
)


def _calculate_vtho(t_1, t_2, vetAmount):
    '''' 5x10^(-9) vtho per vet per second '''
    assert t_1 <= t_2
    return vetAmount * (t_2 - t_1) * 5 / (10**9)


def test_example(router02_contract):
    print(router02_contract)