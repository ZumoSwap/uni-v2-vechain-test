# Test the generation of VTHO of different type of pools
# Test the share of VTHO of different users
# Test the withdraw of VTHO of different users

import time
import pytest
from thor_requests import connect
from thor_requests.connect import Connect
from thor_requests.contract import Contract
from thor_requests.wallet import Wallet
from .helpers import (
    helper_replay,
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
    router02_contract,
    v2pair_contract,
    erc20_contract
)

AMOUNT = 1000 * (10 ** 18)

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


def _view_total_lp(connector:Connect, pool_addr:str, pool_contract:Contract):
    best_block = connector.get_block()
    current_timestamp = best_block['timestamp']
    r, res = helper_call(connector, None, pool_addr, pool_contract, 'totalSupply', [])
    assert r == False
    lp = int(res['decoded']['0'])
    return current_timestamp, lp


def _view_vtho(connector:Connect, user_addr:str, vtho_addr:str, vtho_contract:Contract):
    ''' View VTHO of a single address '''
    best_block = connector.get_block()
    current_timestamp = best_block['timestamp']
    r, res = helper_call(connector, user_addr, vtho_addr, vtho_contract, 'balanceOf', [user_addr])
    assert r == False
    lp = int(res['decoded']['0'])
    return current_timestamp, lp


def _view_vvet(connector:Connect, user_addr:str, vvet_addr:str, vvet_contract:Contract):
    ''' View VVET of a single address '''
    best_block = connector.get_block()
    current_timestamp = best_block['timestamp']
    r, res = helper_call(connector, user_addr, vvet_addr, vvet_contract, 'balanceOf', [user_addr])
    assert r == False
    lp = int(res['decoded']['0'])
    return current_timestamp, lp


def _view_vtho_interest_on_vvet(connector:Connect, user_addr:str, vvet_addr:str, vvet_contract:Contract):
    ''' On VVET contract: view VTHO of an address that is generated because of holding vvet '''
    best_block = connector.get_block()
    current_timestamp = best_block['timestamp']
    r, res = helper_call(connector, user_addr, vvet_addr, vvet_contract, 'vthoBalance', [user_addr])
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
    
    helper_wait_for_block(connector)

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
    if r == True:
        result = helper_replay(connector, receipt['meta']['txID'])
        print(result)
    
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
    helper_wait_for_block(connector)

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


def _view_contribution_on_pool(connector:Connect, pool_addr:str, pool_contract:Contract, user_addr:str=None):
    ''' View contribution of a user to the pool, if not specified view the total contribution '''
    best_block = connector.get_block()
    current_timestamp = best_block['timestamp']
    if user_addr:
        r, res = helper_call(connector, None, pool_addr, pool_contract, 'viewContribution', [user_addr])
    else:
        r, res = helper_call(connector, None, pool_addr, pool_contract, 'viewTotalContribution', [])
    assert r == False
    return current_timestamp, int(res['decoded']['0'])


def _view_claimable_vtho_on_pool(connector:Connect, pool_addr:str, pool_contract: Contract, user_addr:str=None):
    ''' View the vtho of LP user on a pool '''
    best_block = connector.get_block()
    current_timestamp = best_block['timestamp']
    if user_addr:
        r, res = helper_call(connector, user_addr, pool_addr, pool_contract, 'viewUserGeneratedVTHO', [user_addr])
    else:
        r, res = helper_call(connector, None, pool_addr, pool_contract, 'viewTotalGeneratedVTHO', [])
    assert r == False
    return current_timestamp, int(res['decoded']['0'])    


def _claim_bonus_vtho_on_pool(connector:Connect, wallet:Wallet, receiver_addr:str, pool_addr:str, pool_contract: Contract):
    ''' User claim his vtho on the pool '''
    r, receipt = helper_transact(
        connector,
        wallet,
        pool_addr,
        pool_contract,
        'claimGeneratedVTHO',
        [receiver_addr]
    )
    assert r == False
    packed_timestamp = receipt['meta']['blockTimestamp']
    # print('receipt', receipt)
    assert type(packed_timestamp) == int
    return packed_timestamp


def test_vvet_vtho_pool(connector, wallet, factory_contract, v2pair_contract, erc20_contract, router02_contract, vvet_contract, deployed_vvet, deployed_factory, deployed_router02, vtho_contract_address):
    '''
        1) creation of vvet/vtho pool
        2) user deposit, check pool vvet/vtho balance
        3) per block, check total contribution, user contribution (if they match)
        4) per block, check total vtho generated, user vtho claimable (if they match)
        5) remove all vvet/vtho
        6) per block, check growth of contribution, growth of vtho generated. (if they match)
        7) user claim all the extra vtho generated.
        8) per block, check contribution, vtho generated (to be 0)
    '''
    # create a pool of vet/vtho
    t_1, pool_addr = _create_or_check_pool(connector, deployed_vvet, vtho_contract_address, deployed_factory, factory_contract, wallet)
    assert pool_addr != None

    # user lp is 0
    t_2, lp = _view_lp_of_user(connector, wallet.getAddress(), pool_addr, v2pair_contract)
    assert lp == 0

    # user contribution to the pool is 0
    t_2_1, contrib = _view_contribution_on_pool(connector, pool_addr, v2pair_contract, wallet.getAddress())
    assert contrib == 0

    # total contribution of pool is 0
    t_2_2, contrib_total = _view_contribution_on_pool(connector, pool_addr, v2pair_contract)
    assert contrib_total == 0

    # user deposit 1000 VET + 1000 VTHO, gain some lp
    t_3 = _add_lp_vet_vtho(AMOUNT, AMOUNT, vtho_contract_address, erc20_contract, deployed_router02, router02_contract, connector, wallet)

    # user shall have some lp now
    t_4, lp = _view_lp_of_user(connector, wallet.getAddress(), pool_addr, v2pair_contract)
    print('user lp:', lp)
    assert lp > 0
    
    # total lp should not be zero
    t_4_2, total_lp = _view_total_lp(connector, pool_addr, v2pair_contract)
    # Initial deduct of uni-v2 mint:sub(MINIMUM_LIQUIDITY), about 1000 lp goes to address(0)
    assert lp + 1000 == total_lp
    print('total lp:', total_lp)

    # check contribution
    helper_wait_for_block(connector)
    t_5, c_1 = _view_contribution_on_pool(connector, pool_addr, v2pair_contract, wallet.getAddress())
    t_6, c_2 = _view_contribution_on_pool(connector, pool_addr, v2pair_contract, None)
    assert t_5 == t_6
    print('user contribution:', c_1)
    assert c_2 > 0
    print('total contribution:', c_2)
    assert c_1 > 0

    # check vtho claimable (which is generated by holding the lp)
    helper_wait_for_block(connector)
    t_7, cv_7 = _view_claimable_vtho_on_pool(connector, pool_addr, v2pair_contract, wallet.getAddress())
    print('vtho claimable by user:', cv_7)
    t_8, cv_8 = _view_claimable_vtho_on_pool(connector, pool_addr, v2pair_contract, None)
    print('vtho claimable by pool:', cv_8)
    # vtho generated by holding vvet (owner is the pool)
    t_9, cv_9 = _view_vtho_interest_on_vvet(connector, pool_addr, deployed_vvet, vvet_contract)
    print('vtho generated by pool on vvet.sol:', cv_9)
    # vtho in the pool (provided from lp, owner is the pool)
    t_10, cv_10 = _view_vtho(connector, pool_addr, vtho_contract_address, erc20_contract)
    print('vtho held by the pool (provided by lp):', cv_10)
    t_10_1, cv_10_1 = _view_vvet(connector, pool_addr, deployed_vvet, erc20_contract)
    print('vvet held by the pool (provided by lp):', cv_10_1)
    # vtho generated by the vvet (owner is the pool, generated by vet)
    t_11, cv_11 = _view_vtho(connector, deployed_vvet, vtho_contract_address, erc20_contract)
    print('total vtho in vvet.sol:', cv_11)
    assert t_7 == t_8
    assert t_7 == t_9
    assert t_7 == t_10
    assert t_7 == t_11
    assert cv_7 <= cv_8 # user contribution cannot exceed total contribution
    assert cv_8 == cv_9
    assert cv_10 == AMOUNT
    assert cv_9 == cv_11

    # user remove all liquidity of the user
    t_12 = _remove_lp_vet_vtho(pool_addr, v2pair_contract, lp, vtho_contract_address, deployed_router02, router02_contract, connector, wallet)
    print('user removed all lp')
    helper_wait_for_block(connector)

    t_12_1, total_lp = _view_total_lp(connector, pool_addr, v2pair_contract)
    print('total lp:', total_lp)
    assert total_lp == 1000
    t_12_2, user_lp = _view_lp_of_user(connector, wallet.getAddress(), pool_addr, v2pair_contract)
    print('user lp:', user_lp)
    assert user_lp == 0

    # check contribution, claimable vtho growth
    t_13, cv_13 = _view_claimable_vtho_on_pool(connector, pool_addr, v2pair_contract, wallet.getAddress())
    print('vtho claimable by user:', cv_13)
    t_14, cv_14 = _view_claimable_vtho_on_pool(connector, pool_addr, v2pair_contract, None)
    print('vtho claimable by pool:', cv_14)
    assert t_13 == t_14
    assert cv_13 <= cv_14

    t_15, c_15 = _view_contribution_on_pool(connector, pool_addr, v2pair_contract, wallet.getAddress())
    print('user contribution to pool:', c_15)
    t_16, c_16 = _view_contribution_on_pool(connector, pool_addr, v2pair_contract)
    print('pool total contribution:', c_16)
    assert t_15 == t_16
    assert c_15 > 0
    assert c_16 >= c_15

    # wait for another block
    helper_wait_for_block(connector)

    # check if the growth is stopped
    t_17, cv_17 = _view_claimable_vtho_on_pool(connector, pool_addr, v2pair_contract, wallet.getAddress())
    print('vtho claimable by user:', cv_17)
    t_18, cv_18 = _view_claimable_vtho_on_pool(connector, pool_addr, v2pair_contract, None)
    print('vtho claimable by pool:', cv_14)
    assert t_17 == t_18
    assert cv_17 == cv_13 # vtho interest stop growth of the user
    assert cv_18 == cv_14 # vtho interest stop growth of pool

    t_19, c_19 = _view_contribution_on_pool(connector, pool_addr, v2pair_contract, wallet.getAddress())
    print('user contribution to pool:', c_19)
    t_20, c_20 = _view_contribution_on_pool(connector, pool_addr, v2pair_contract)
    print('pool total contribution:', c_16)
    assert t_19 == t_20
    assert c_19 == c_15 # user contribution shall stop growing (all lp token removed).
    assert c_20 >= c_16 # address(0) holds 1000 lp token, still generating contribution

    # user remove the vtho generated (claimable)
    _, user_vtho_1 = _view_vtho(connector, wallet.getAddress(), vtho_contract_address, erc20_contract)
    print('vtho in user wallet before claim:', user_vtho_1)
    print('user claimable vtho from pool:', cv_17)
    t_21 = _claim_bonus_vtho_on_pool(connector, wallet, wallet.getAddress(), pool_addr, v2pair_contract)
    _, user_vtho_2 = _view_vtho(connector, wallet.getAddress(), vtho_contract_address, erc20_contract)
    print('vtho in user wallet after claim:', user_vtho_2)

    # user shall have 0 contribution and 0 claimable vtho on pool
    t_21, cv_21 = _view_claimable_vtho_on_pool(connector, pool_addr, v2pair_contract, wallet.getAddress())
    print('vtho claimable by user:', cv_21)
    t_22, cv_22 = _view_claimable_vtho_on_pool(connector, pool_addr, v2pair_contract, None)
    print('vtho claimable by pool:', cv_22)
    assert t_21 == t_22
    assert cv_21 == 0
    assert cv_22 > 0

    t_23, c_23 = _view_contribution_on_pool(connector, pool_addr, v2pair_contract, wallet.getAddress())
    print('user contribution to pool:', c_23)
    t_24, c_24 = _view_contribution_on_pool(connector, pool_addr, v2pair_contract)
    print('pool total contribution:', c_24)
    assert t_23 == t_24
    assert c_23 == 0
    assert c_24 > 0


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
