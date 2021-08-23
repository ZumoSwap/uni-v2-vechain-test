# Test the generation of VTHO of different type of pools
# Test the share of VTHO of different users
# Test the withdraw of VTHO of different users

import time
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
    solo_wallet as wallet,  # wallet with big money inside
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


def _calculate_vtho(t_1, t_2, vetAmount):
    '''' 5x10^(-9) vtho per vet per second '''
    assert t_1 <= t_2
    return vetAmount * (t_2 - t_1) * 5 / (10**9)


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
    packed_timestamp = receipt['meta']['blockTimestamp']
    return packed_timestamp, pool_addr


def _view_lp_of_user(connector:Connect, user_addr:str, pool_addr:str, pool_contract:Contract):
    best_block = connector.get_block()
    current_timestamp = best_block['timestamp']
    r, res = helper_call(connector, user_addr, pool_addr, pool_contract, 'balanceOf', [user_addr])
    assert r == False
    lp = int(res['decoded']['0'])
    return current_timestamp, lp


def _add_lp_vet_vtho(amount_vet:int, amount_vtho:int, vtho_addr:str, vtho_contract:Contract, router_addr:str, router:Contract, connector:Connect, wallet:Wallet):
    ''' Helper: Add liquidity to vvet/vtho pair '''
    # Approve some vtho
    r, receipt = helper_transact(
        connector,
        wallet,
        vtho_addr,
        vtho_contract,
        'approve',
        [router_addr, amount_vtho]
    )
    assert r == False
    
    helper_wait_for_block()

    # Add LP
    r, receipt = helper_transact(
        connector,
        wallet,
        router_addr,
        router,
        'addLiquidityETH',
        [vtho_addr, amount_vtho, int(amount_vtho * 0.9), int(amount_vet * 0.9), wallet.getAddress(), int(time.time()) + 1000],
        amount_vet
    )
    assert r == False
    packed_timestamp = receipt['meta']['blockTimestamp']
    assert type(packed_timestamp) == int

    # timestamp
    return packed_timestamp


def _remove_lp_vet_vtho(pool_addr:str, pool_contract:Contract, amount_lp:int, vtho_addr:str, router_addr:str, router:Contract, connector:Connect, wallet:Wallet):
    ''' Helper: Remove liquidity of vvet/vtho pair '''
    # Approve
    r, receipt = helper_transact(
        connector,
        wallet,
        pool_addr,
        pool_contract,
        'approve',
        [router_addr, amount_lp]
    )
    assert r == False
    helper_wait_for_block()

    # Remove LP
    r, receipt = helper_transact(
        connector,
        wallet,
        router_addr,
        router,
        'removeLiquidityETH',
        [vtho_addr, amount_lp, 1, 1, wallet.getAddress(), int(time.time()) + 1000]
    )
    assert r == False
    packed_timestamp = receipt['meta']['blockTimestamp']
    assert type(packed_timestamp) == int

    # timestamp
    return packed_timestamp


def _swap_vet_to_vtho(amount_vet:int, vet_addr:str, vtho_addr:str, router_addr:str, router:Contract, connector:Connect, wallet:Wallet):
    ''' Helper: Swap some VET to VTHO (no matter what amount) '''
    # Swap
    r, receipt = helper_transact(
        connector,
        wallet,
        router_addr,
        router,
        'swapExactEthForTokens',
        [1, [vet_addr, vtho_addr], wallet.getAddress(), int(time.time()) + 1000],
        amount_vet
    )
    assert r == False
    packed_timestamp = receipt['meta']['blockTimestamp']
    assert type(packed_timestamp) == int
    return packed_timestamp


def _view_contribution(connector:Connect, pool_addr:str, user_addr=None):
    ''' Helper: View contribution of a user, if not specified view the total contribution '''
    pass


def _view_vtho_claimable(connector:Connect, pool_addr:str, user_addr=None):
    ''' Helper: Vew vtho claimable of a user, if not specified view the total claimable '''
    pass


def _claim_vtho(connector:Connect, wallet:Wallet, pool_addr:str, amount_vtho:int):
    ''' Helper: Claim some vtho generated (or bonus) '''
    pass


def test_vvet_vtho_pool(connector, wallet, factory_contract, deployed_vvet, deployed_factory, deployed_router02, vtho_contract_address):
    '''
        1) creation of vvet/vtho pool
        2) user deposit, check vvet/vtho balance
        3) per block, check total contribution, user contribution (if they match)
        4) per block, check total vtho generated, user vtho claimable (if they match)
        5) remove all vvet/vtho
        6) per block, check growth of contribution, growth of vtho generated. (if they match)
        7) user claim all the vtho generated.
        8) per block, check contribution, vtho generated (to be 0)
    '''
    t_1, pool_addr = _create_or_check_pool(connector, deployed_vvet, vtho_contract_address, deployed_factory, factory_contract, wallet)
    assert pool_addr != None


def test_vvet_vtho_pool_2():
    '''
        1) creation of vvet/vtho pool
        2) user1 deposit, check vvet/vtho balance
        3) user2 deposit, check vvet/vtho balance
        4) per block, check contribution (total, user1, user2)
        5) same time check vtho generated/claimable (total, user1, user2)
        6) user1 withdraw all vvet/vtho
        7) per block, check contribution and vtho generated if match
    '''
    pass


def test_vvet_vtho_pool_3():
    '''
        1) creation of vvet/vtho pool
        2) user1 deposit, check vvet/vtho balance
        3) user2 swap
        4) per block, check user contribution, vtho generated, vtho claimable (total, user1)
        5) user2 swap
        6) per block, check user coontribution, vtho generated, vtho claimable (total, user1)
    '''
    pass


def test_vvet_vtho_pool_4():
    '''
        1) creation of vvet/vtho pool
        2) user1 deposit, check vvet/vtho balance
        3) user2 deposit, check vvet/vtho balance
        4) per block, check user contribution, vtho generated, claimable
        5) admin airdrop directly some vtho into VVET smart contract (emulate bonus process).
        6) per block, check user contribution, vtho generated, claimable
    '''
    pass
