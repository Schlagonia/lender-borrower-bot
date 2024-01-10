from typing import Optional
from ape import project
from ape.contracts import ContractInstance
from scripts.univ3 import amounts_for_liquidity, sqrt_price_to_amount
from scripts.univ3_graph import pool_24hr_volume


def iv_from_pool(pool: str | ContractInstance, end_time=None):
    if isinstance(pool, str):
        pool = project.UniV3Pool.at(pool)
    token0 = project.IERC20Extended.at(pool.token0())
    token1 = project.IERC20Extended.at(pool.token1())
    decimal_diff = token0.decimals() - token1.decimals()

    fee_tier = pool.fee() / 1e6

    tick_liquidity = pool.liquidity()
    slot0 = pool.slot0()
    tick = slot0["tick"]
    sqrt_price_x96 = slot0["sqrtPriceX96"]
    token_0_amount, token_1_amount = amounts_for_liquidity(
        sqrt_price_x96, tick, tick + pool.tickSpacing(), tick_liquidity
    )
    token_0_amount /= 10 ** token0.decimals()
    token_1_amount /= 10 ** token1.decimals()

    volume = pool_24hr_volume(
        pool.address, end_time=end_time, chain_id=project.chain_manager.chain_id
    )["volumeToken0"]

    price = sqrt_price_to_amount(sqrt_price_x96) * 10**decimal_diff
    price = price**-1
    tick_tvl = token_0_amount + token_1_amount * price

    iv_val = iv(fee_tier, volume, tick_tvl)

    return iv_val


def iv(fee_tier, volume, tick_tvl):
    return (2 * fee_tier * volume**0.5) / (tick_tvl**0.5) * (365**0.5)


import click
from ape.cli import network_option, NetworkBoundCommand


@click.command(cls=NetworkBoundCommand)
@click.option("--pool", "pool", required=True)
@click.option("--end-time", "end_time", default=None, type=int)
@network_option()
def cli(pool, end_time, **_):
    print(f"{iv_from_pool(pool, end_time):.2%}")
