from time import time
from datetime import datetime
import os
import json
from web3 import Web3
import math
from io import StringIO
import telegram
from rich import print
import requests
from ape import project, chain, Contract, networks

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
telegram_bot_key = ""
telegram_chat_id = int(-1001553383497)

list_of_strategies = {
    "ethereum": [
            "0x9E9a2a86eeff52FFD13fc724801a4259b2B1A949"
    ],
}

summary_msg = "\n=== CompV3 Lender Borrower SUMMARY ===\n"

def _lender_borrower_status():
    now_unix = time()

    chain = networks.provider.network.ecosystem.name
    
    print(
        f"{'ETH' if chain == 'ethereum' else 'Polygon'} Strategy Status {datetime.utcfromtimestamp(now_unix).isoformat()}:"
    )
    global summary_msg

    for strategy_address in list_of_strategies[chain]:
        print("\n---\n")

        strategy = Contract(strategy_address)

        name = strategy.name()
        vault = Contract(strategy.vault())

        debt = vault.strategies(strategy.address)["totalDebt"]

        if debt == 0:
            print(f"\n{name}: Inactive Strategy")
        
        else:
            token = Contract(strategy.want())
            token_decimals = token.decimals()
            token_symbol = token.symbol()

            depositer = Contract(strategy.depositer())
            borrower = Contract(strategy.baseToken())
            borrower_decimals = borrower.decimals()
            borrower_symbol = borrower.symbol()

            comet = Contract(strategy.comet())
            last_harvest_UNIX = vault.strategies(strategy)["lastReport"]

            # need to adjust based on chain
            reward_token = Contract("0xc00e94Cb662C3520282E6f5717214004A7f26888")

            token_price_feed = strategy.priceFeeds(token)
            borrower_price_feed = strategy.priceFeeds(borrower)
            reward_price_feed = ""

            token_price = comet.getPrice(token_price_feed)

            borrower_price = comet.getPrice(borrower_price_feed)
            reward_price = 0

            if reward_token != ZERO_ADDRESS:
                reward_price_feed = strategy.priceFeeds(reward_token)
                reward_price = comet.getPrice(reward_price_feed)
            
            borrowed = strategy.balanceOfDebt()
            depositer_balance = depositer.cometBalance()
            base_token_owed = strategy.baseTokenOwedBalance()

            current_ltv =strategy.getCurrentLTV() 
            target_ltv = strategy.getLiquidateCollateralFactor() * strategy.targetLTVMultiplier() / 10_000 
            warning_ltv = strategy.getLiquidateCollateralFactor() * strategy.warningLTVMultiplier() / 10_000 

            net_borrow_apr = depositer.getNetBorrowApr(0)
            net_reward_apr = depositer.getNetRewardApr(0)
            net_apr = net_reward_apr - net_borrow_apr

            days_from_harvest = int((now_unix - last_harvest_UNIX) / 86400)
            hours_from_harvest = int(
                (now_unix - last_harvest_UNIX - (days_from_harvest * 86400)) / 3600
            )
            dur_since_last_harvest_yrs = 365 / ((now_unix - last_harvest_UNIX) / 86400)

            harvest_trigger_status = strategy.harvestTrigger(100)
            tend_trigger_status = strategy.tendTrigger(100)

            profit = 0
            """
            logs = simulate_harvest(strategy)

            for log in logs:
                if log["name"] == "StrategyReported":
                    profit = log["inputs"][1]["value"]
            """
            
            """
            keeper = vault.governance()
            tx = strategy.harvest(sender=keeper)
            event = list(tx.decode_logs(vault.StrategyReported))

            profit = event[0].gain
            """
            profit_usd = (
                profit / (10 ** token_decimals)
            ) * token_price

            APR = (
                profit
                * dur_since_last_harvest_yrs
                / debt
            )
            
            print(f"{name}:")
            print(f"Last Harvest: {days_from_harvest}d, {hours_from_harvest}h ago")
            print(f"\n=== Current Balances ===")
            print(
                f"Collateral: {token_symbol}: {debt /(10 ** token_decimals):,.2f} (${debt *token_price / (10 ** (8 + token_decimals)):,.2f})"
            )
            print(
                f"Debt {borrower_symbol}: {borrowed / (10 ** borrower_decimals):,.2f}, (${borrowed * borrower_price / (10 ** (borrower_decimals + 8)):,.2f})"
            )
            print(
                f"Depositer {borrower_symbol}: {depositer_balance / (10 ** borrower_decimals):,.2f}, (${depositer_balance * borrower_price / (10 ** (borrower_decimals + 8)):,.2f})"
            )
            print(
                f"Owed {borrower_symbol}: {base_token_owed / (10 ** borrower_decimals):,.2f}, (${base_token_owed * borrower_price / (10 ** (borrower_decimals + 8)):,.2f})"
            )

            print(f"\n=== LTV ===")
            
            print(f"Current Strategy LTV: {current_ltv/ 1e16 :,.2f}%")
            
            print(f"Target LTV: {target_ltv / 1e16 :,.2f}%")
            
            print(f"Warning LTV: {warning_ltv / 1e16 :,.2f}%")
            print(f"Liquidation LTV: {strategy.getLiquidateCollateralFactor() / 1e16 :,.2f}%")

            
            print(f"\n=== Current Apy's  ===")
            print(f"Current net borrowe apr -{(net_borrow_apr / 1e16):,.2f}%")
            print(f"Current Reward Apr: {(net_reward_apr/1e16):,.2f}%")
            print(f"Net apy {(net_apr/1e16):,.2f}%")

            summary_msg += "\n" + name + "\n"
            summary_msg += f"LTV: {current_ltv/ 1e16 :,.2f}%" + "\n"

            if profit > 0:
                print(f"\n=== Expected Return ===")
                print(
                    f"{token_symbol}: {profit/(10 ** token_decimals):,.4f}, (${profit_usd / 1e8 :,.2f})"
                )
                print(f"APR : {APR:,.4%}")
                summary_msg += f"APR: {APR:,.2%}" + "\n"
        
            print(f"\n=== Triggers ===")
            print(f"Strategy Harvest Trigger: {harvest_trigger_status}")
            print(f"Strategy Tend Trigger: {tend_trigger_status}")

    print("\n---\n")
    print(summary_msg)


def simulate_harvest(strategy):
    encoded_input = strategy.harvest.encode_input()

    user = os.environ["USER"]
    project = os.environ["PROJECT"]
    key = os.environ["TENDERLY_SIM_KEY"]

    url = f"https://api.tenderly.co/api/v1/account/{user}/project/{project}/simulate"
    headers = {"x-access-key": key}

    body = {
        "network_id": 1,
        "from": strategy.keeper(),
        "to": strategy.address,
        "input": encoded_input,
        "gas": 8_000_000,
        "gas_price": "0",
    }

    r = requests.post(url, json=body, headers=headers)

    j = r.json()

    return j["transaction"]["transaction_info"]["call_trace"]["logs"]


def main():
    _lender_borrower_status()