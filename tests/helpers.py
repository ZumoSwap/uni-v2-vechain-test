from thor_requests import utils
from thor_requests.connect import Connect
from thor_requests.contract import Contract
from thor_requests.wallet import Wallet

def helper_replay(connector: Connect, tx_id: str):
    return connector.replay_tx(tx_id)

def helper_deploy(connector: Connect, wallet: Wallet, contract: Contract, param_types=None, params=None) -> str:
    ''' Deploy a smart contract and return the created contract address'''
    res = connector.deploy(wallet, contract, param_types, params, 0)
    assert "id" in res
    receipt = connector.wait_for_tx_receipt(res["id"])
    created_contracts = utils.read_created_contracts(receipt)
    assert len(created_contracts) == 1
    return created_contracts[0]

def helper_call(connector:Connect, caller:str, contract_addr:str, contract:Contract, func_name:str, func_params:list, value:int=0):
    '''Call on-chain, return reverted(bool), response'''
    if caller == None:
        caller = '0x0000000000000000000000000000000000000000'
    res = connector.call(
        caller,
        contract,
        func_name,
        func_params,
        contract_addr,
        value=value
    )
    return res["reverted"], res

def helper_transact(connector:Connect, wallet:Wallet, contract_addr:str, contract:Contract, func_name:str, func_params:list, value:int=0):
    '''Transact on-chain, and return reverted(bool), receipt'''
    res = connector.transact(
        wallet,
        contract,
        func_name,
        func_params,
        contract_addr,
        value=value,
        force=True
    )
    assert res["id"]
    receipt = connector.wait_for_tx_receipt(res["id"])
    return receipt["reverted"], receipt

def helper_wait_for_block(connector:Connect, number:int=1):
    counter = 0
    for block in connector.ticker():
        counter += 1
        if counter >= number:
            break
