from requests import Session as ClientSession
from requests.adapters import HTTPAdapter, Retry
import json
from time import time

ONE_DAY_SECONDS = 86400

api_key = "fdf9426357fa1d0bbc42a28c8f03304c"


def pool_24hr_volume(pool, end_time=None, chain_id=1):
    if end_time is None:
        block_one_day_ago = block_at_time(time() - ONE_DAY_SECONDS, chain_id=chain_id)
        volume_end = pool_volume(pool, chain_id=chain_id)
        volume_start = pool_volume(
            pool,
            block_one_day_ago,
            chain_id=chain_id,
        )
    else:
        block_at_end = block_at_time(end_time, chain_id=chain_id)
        block_at_start = block_at_time(end_time-ONE_DAY_SECONDS, chain_id=chain_id)
        volume_end = pool_volume(
            pool,
            block_at_end,
            chain_id=chain_id,
        )
        volume_start = pool_volume(
            pool,
            block_at_start,
            chain_id=chain_id,
        )

    net_volume_24hrs = {
        key: (volume_end[key] - volume_start[key])
        for key in volume_end.keys()
        if key != "id"
    }

    return net_volume_24hrs


def pool_volume(pool, block=None, chain_id=1):
    query = (
        "{\n"
        "  pool(\n"
        f'      id: "{pool.lower():s}"\n'
        f"{'      block: {{ number: {} }}'.format(block) if block != None else ''}"
        "\n"
        "   ){\n"
        "       id\n"
        "       volumeUSD\n"
        "       volumeToken0\n"
        "       volumeToken1\n"
        "   }\n"
        "}"
    )

    url = (
        "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
        if chain_id == 1
        else "https://api.thegraph.com/subgraphs/name/ianlapham/uniswap-v3-polygon"
    )
    r = _get_http_session().post(
        url, json={"query": query}, headers={"Authorization": f"Bearer {api_key}"}
    )
    assert r.status_code == 200
    pool_data = json.loads(r.text)["data"]["pool"]
    assert pool.lower() == pool_data["id"].lower()
    pool_data["volumeUSD"] = float(pool_data["volumeUSD"])
    pool_data["volumeToken0"] = float(pool_data["volumeToken0"])
    pool_data["volumeToken1"] = float(pool_data["volumeToken1"])

    return pool_data


def block_at_time(time, chain_id=1) -> int | None:
    query = (
        "{\n"
        "  blocks(\n"
        "           first: 1\n"
        "           skip: 0\n"
        "           orderBy: number\n"
        "           orderDirection: asc\n"
        f"           where: {{timestamp_gte: {int(time)}, timestamp_lt: {int(time)+60}}}\n"
        "  ) {\n"
        "    id\n"
        "    number\n"
        "    timestamp\n"
        "  }\n"
        "}\n"
    )

    url = (
        "https://api.thegraph.com/subgraphs/name/blocklytics/ethereum-blocks"
        if chain_id == 1
        else "https://api.thegraph.com/subgraphs/name/ianlapham/polygon-blocks"
    )
    r = _get_http_session().post(
        url,
        json={"query": query},
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=120,
    )
    assert r.status_code == 200
    blocks = json.loads(r.text)["data"]["blocks"]
    if len(blocks) == 0:
        return None
    block_number = int(blocks[0]["number"], 10)
    return block_number


def _get_http_session() -> ClientSession:
    client_session = ClientSession()
    retries = Retry(
        total=5,
        status_forcelist=[400, 403, 429, 500, 503],
    )
    client_session.mount("http://", HTTPAdapter(max_retries=retries))
    return client_session


