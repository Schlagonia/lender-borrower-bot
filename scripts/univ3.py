FIXED_POINT_RESOLUTION = 96
FIXED_POINT_Q96 = 0x1000000000000000000000000
MAX_TICK = 887272


def sqrt_price_to_amount(sqrt_price_x96):
    return (sqrt_price_x96 / FIXED_POINT_Q96) ** 2


def amount_to_sqrt_price(amount):
    return (amount**0.5) * FIXED_POINT_Q96


def amounts_for_liquidity(sqrt_price_x96, tick_lower, tick_upper, liquidity):
    sqrt_ratio_a_x96 = sqrt_ratio_at_tick(tick_lower)
    sqrt_ratio_b_x96 = sqrt_ratio_at_tick(tick_upper)

    if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
        (sqrt_ratio_a_x96, sqrt_ratio_b_x96) = (sqrt_ratio_b_x96, sqrt_ratio_a_x96)

    amount0 = amount1 = 0

    if sqrt_price_x96 <= sqrt_ratio_a_x96:
        amount0 = amount0_for_liquidity(sqrt_ratio_a_x96, sqrt_ratio_b_x96, liquidity)
    elif sqrt_price_x96 < sqrt_ratio_b_x96:
        amount0 = amount0_for_liquidity(sqrt_price_x96, sqrt_ratio_b_x96, liquidity)
        amount1 = amount1_for_liquidity(sqrt_ratio_a_x96, sqrt_price_x96, liquidity)
    else:
        amount1 = amount1_for_liquidity(sqrt_ratio_a_x96, sqrt_ratio_b_x96, liquidity)

    return amount0, amount1


def amount0_for_liquidity(sqrt_ratio_a_x96, sqrt_ratio_b_x96, liquidity):
    if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
        (sqrt_ratio_a_x96, sqrt_ratio_b_x96) = (sqrt_ratio_b_x96, sqrt_ratio_a_x96)

    return (
        (
            (int(liquidity) << FIXED_POINT_RESOLUTION)
            * int(sqrt_ratio_b_x96 - sqrt_ratio_a_x96)
        )
        / int(sqrt_ratio_b_x96)
    ) / int(sqrt_ratio_a_x96)


def amount1_for_liquidity(sqrt_ratio_a_x96, sqrt_ratio_b_x96, liquidity):
    if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
        (sqrt_ratio_a_x96, sqrt_ratio_b_x96) = (sqrt_ratio_b_x96, sqrt_ratio_a_x96)
    return (int(liquidity) * int(sqrt_ratio_b_x96 - sqrt_ratio_a_x96)) / FIXED_POINT_Q96


def sqrt_ratio_at_tick(tick):
    abs_tick = -tick if tick < 0 else tick
    assert abs_tick <= MAX_TICK

    ratio = int(
        0xFFFCB933BD6FAD37AA2D162D1A594001
        if abs_tick & 0x1 != 0
        else 0x100000000000000000000000000000000
    )
    if abs_tick & 0x2 != 0:
        ratio = (ratio * 0xFFF97272373D413259A46990580E213A) >> 128
    if abs_tick & 0x4 != 0:
        ratio = (ratio * 0xFFF2E50F5F656932EF12357CF3C7FDCC) >> 128
    if abs_tick & 0x8 != 0:
        ratio = (ratio * 0xFFE5CACA7E10E4E61C3624EAA0941CD0) >> 128
    if abs_tick & 0x10 != 0:
        ratio = (ratio * 0xFFCB9843D60F6159C9DB58835C926644) >> 128
    if abs_tick & 0x20 != 0:
        ratio = (ratio * 0xFF973B41FA98C081472E6896DFB254C0) >> 128
    if abs_tick & 0x40 != 0:
        ratio = (ratio * 0xFF2EA16466C96A3843EC78B326B52861) >> 128
    if abs_tick & 0x80 != 0:
        ratio = (ratio * 0xFE5DEE046A99A2A811C461F1969C3053) >> 128
    if abs_tick & 0x100 != 0:
        ratio = (ratio * 0xFCBE86C7900A88AEDCFFC83B479AA3A4) >> 128
    if abs_tick & 0x200 != 0:
        ratio = (ratio * 0xF987A7253AC413176F2B074CF7815E54) >> 128
    if abs_tick & 0x400 != 0:
        ratio = (ratio * 0xF3392B0822B70005940C7A398E4B70F3) >> 128
    if abs_tick & 0x800 != 0:
        ratio = (ratio * 0xE7159475A2C29B7443B29C7FA6E889D9) >> 128
    if abs_tick & 0x1000 != 0:
        ratio = (ratio * 0xD097F3BDFD2022B8845AD8F792AA5825) >> 128
    if abs_tick & 0x2000 != 0:
        ratio = (ratio * 0xA9F746462D870FDF8A65DC1F90E061E5) >> 128
    if abs_tick & 0x4000 != 0:
        ratio = (ratio * 0x70D869A156D2A1B890BB3DF62BAF32F7) >> 128
    if abs_tick & 0x8000 != 0:
        ratio = (ratio * 0x31BE135F97D08FD981231505542FCFA6) >> 128
    if abs_tick & 0x10000 != 0:
        ratio = (ratio * 0x9AA508B5B7A84E1C677DE54F3E99BC9) >> 128
    if abs_tick & 0x20000 != 0:
        ratio = (ratio * 0x5D6AF8DEDB81196699C329225EE604) >> 128
    if abs_tick & 0x40000 != 0:
        ratio = (ratio * 0x2216E584F5FA1EA926041BEDFE98) >> 128
    if abs_tick & 0x80000 != 0:
        ratio = (ratio * 0x48A170391F7DC42444E8FA2) >> 128

    if tick > 0:
        ratio = (2**256 - 1) / int(ratio)

    # this divides by 1<<32 rounding up to go from a Q128.128 to a Q128.96.
    # we then downcast because we know the result always fits within 160 bits due to our tick input constraint
    # we round up in the division so getTickAtSqrtRatio of the output price is always consistent
    return (int(ratio) >> 32) + (0 if ratio % (1 << 32) == 0 else 1)


def get_tick_at_sqrt_ratio(sqrt_ratio_x96):
    sqrt_ratio_x128 = int(sqrt_ratio_x96) << 32

    msb = _msb(sqrt_ratio_x128)

    r = 0
    if msb >= 128:
        r = sqrt_ratio_x128 >> (msb - 127)
    else:
        r = sqrt_ratio_x128 << (127 - msb)

    log_2 = (msb - 128) << 64

    for i in range(14):
        r = (r * r) >> 127
        f = r >> 128
        log_2 = log_2 | (f << (63 - i))
        r = r >> f

    log_sqrt10001 = log_2 * int(255738958999603826347141)

    tick_low = (log_sqrt10001 - int(3402992956809132418596140100660247210)) >> 128
    tick_high = (log_sqrt10001 + int(291339464771989622907027621153398088495)) >> 128

    if tick_low == tick_high:
        return tick_low
    if sqrt_ratio_at_tick(tick_high) <= sqrt_ratio_x96:
        return tick_high
    return tick_low


def _msb(n):
    ndx = 0
    while 1 < n:
        n = n >> 1
        ndx += 1

    return ndx
