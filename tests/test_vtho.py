# Test the generation of VTHO of different type of pools
# Test the share of VTHO of different users
# Test the withdraw of VTHO of different users

import pytest
from thor_requests.connect import Connect
from thor_requests.contract import Contract
from thor_requests.wallet import Wallet
from .helpers import (
    helper_deploy,
    helper_call,
    helper_transact,
    helper_wait_for_block
)
from .fixtures import (
    solo_connector as connector,
    solo_wallet as wallet,
    vtho_contract_address,
    clean_wallet,
    vvet_contract,
    factory_contract,
    router02_contract
)


@pytest.fixture
def deployed_vvet(connector, wallet, vvet_contract):
    return helper_deploy(connector, wallet, vvet_contract)


@pytest.fixture
def deployed_factory(connector, wallet, factory_contract, deployed_vvet):
    # print('inside factory, vvet:', deployed_vvet)
    return helper_deploy(connector, wallet, factory_contract, ['address', 'address'], [wallet.getAddress(), deployed_vvet])


@pytest.fixture
def deployed_router02(connector, wallet, router02_contract, deployed_factory, deployed_vvet):
    # print('inside router02, vvet:', deployed_vvet)
    # print('inside router02, factory:', deployed_factory)
    return helper_deploy(connector, wallet, router02_contract, ['address', 'address'], [deployed_factory, deployed_vvet])


def _create_or_check_pool(connector:Connect, token_1:str, token_2:str, factory_addr:str, factory_contract:Contract, wallet:Wallet) -> str:
    '''create a pool, if pool exists then don't create. Then return the pool address '''
    reverted, response = helper_call(connector, wallet.getAddress(), factory_addr, factory_contract, 'getPair', [token_1, token_2])
    if reverted:
        raise Exception("Call: getPair reverted")
    pool_addr = str(response['decoded']['0'])
    if pool_addr != '0x0000000000000000000000000000000000000000':
        return pool_addr
    reverted, receipt = helper_transact(connector, wallet, factory_addr, factory_contract, 'createPair', [token_1, token_2])
    if reverted:
        raise Exception("Transact: createPair reverted")
    reverted, response = helper_call(connector, wallet.getAddress(), factory_addr, factory_contract, 'getPair', [token_1, token_2])
    if reverted:
        raise Exception("Call: getPair reverted")
    pool_addr = str(response['decoded']['0'])
    return pool_addr


def _calculate_vtho(t_1, t_2, vetAmount):
    '''' 5x10^(-9) vtho per vet per second '''
    assert t_1 <= t_2
    return vetAmount * (t_2 - t_1) * 5 / (10**9)


def test_vvet_vtho_pool(connector, wallet, factory_contract, deployed_vvet, deployed_factory, deployed_router02, vtho_contract_address):
    # print('vvet:', deployed_vvet)
    # print('factory:', deployed_factory)
    # print('router02:', deployed_router02)
    # print('vtho:', vtho_contract_address)
    pool_addr = _create_or_check_pool(connector, deployed_vvet, vtho_contract_address, deployed_factory, factory_contract, wallet)
    assert pool_addr != None