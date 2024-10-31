import sched, time
from datetime import datetime
import math

from . import setup_django_orm  # WARNING : DO NOT REMOVE

from webapp.core.models import Bet, Block, Transaction, UserProfile
from webapp.core.blocks import get_current_or_create_open_block
from webapp.core.wallet.wallet import (
    get_matter_balance,
    send_tokensBSC,
    get_idea_info,
    get_matter_info,
)
from webapp.core.dex.dex import get_token_priceBCS, add_liquidity

from webapp.core.const import (
    APP_WALLET,
    APP_WALLET_PRIVATE_KEY,
    MATTER_TOKEN_ADDRESS,
    IDEA_TOKEN_ADDRESS,
)

BLOCK_REFRESH_PERIOD = 10 * 60


def get_open_block() -> Block:
    # NOTE : Creating open block only happens on the first iteration
    # in case of users not creating any bets for the first 10 minutes
    return get_current_or_create_open_block()


def freeze_block(block: Block) -> Block:
    block.state = 2
    block.save()
    return block


def get_bets() -> list[Bet]:
    return list(Bet.objects.filter(deleted_at__isnull=True, is_active=True))


def deactivate_bets(bets: list[Bet]) -> list[Bet]:
    res: list[Bet] = bets.copy()
    for i in range(len(res)):
        user_profile = UserProfile.objects.get(user=res[i].user)
        matter_balance = get_matter_balance(user_profile.crypto_wallet_address)
        if matter_balance is None or matter_balance < float(res[i].bet_size):
            res[i].is_active = False
            res[i].save()

    return res


def get_active_bets(bets: list[Bet]) -> list[Bet]:
    return [b for b in bets if b.is_active]


def determine_winning_and_loosing_bets(bets: list[Bet]) -> tuple[list[Bet], list[Bet]]:
    current_ratio = float(get_token_priceBCS(IDEA_TOKEN_ADDRESS)) / float(
        get_token_priceBCS(MATTER_TOKEN_ADDRESS)
    )

    sorted_bets = sorted(
        bets,
        key=lambda b: abs(current_ratio - float(b.bet_ratio)),
    )
    winners = sorted_bets[: math.ceil(len(sorted_bets) / 2)]
    loosers = sorted_bets[math.ceil(len(sorted_bets) / 2) :]
    return winners, loosers


def process_winning_bets(bets: list[Bet]):
    cur_ratio = float(get_token_priceBCS(IDEA_TOKEN_ADDRESS)) / float(
        get_token_priceBCS(MATTER_TOKEN_ADDRESS)
    )

    for bet in bets:
        bet.is_winning = True
        bet.save()
        user_profile = UserProfile.objects.get(user=bet.user)
        try:
            bet.bet_ratio = (1 + float(bet.bet_percent) / 100) * cur_ratio
            send_tokensBSC(
                APP_WALLET_PRIVATE_KEY,
                user_profile.crypto_wallet_address,
                IDEA_TOKEN_ADDRESS,
                float(bet.bet_size),
            )
            Transaction.objects.create(
                user=user_profile.user,
                amount=bet.bet_size,
                type=1,
                from_wallet=APP_WALLET,
                to_wallet=user_profile.crypto_wallet_address,
                block=get_current_or_create_open_block(),
                bet=bet,
            )
        except:
            continue


def process_loosing_bets(bets: list[Bet]):
    cur_ratio = float(get_token_priceBCS(IDEA_TOKEN_ADDRESS)) / float(
        get_token_priceBCS(MATTER_TOKEN_ADDRESS)
    )

    for bet in bets:
        bet.is_winning = False
        bet.save()
        user_profile = UserProfile.objects.get(user=bet.user)
        try:
            bet.bet_ratio = (1 + float(bet.bet_percent) / 100) * cur_ratio
            send_tokensBSC(
                user_profile.crypto_wallet_private_key,
                APP_WALLET,
                MATTER_TOKEN_ADDRESS,
                float(bet.bet_size),
            )
            Transaction.objects.create(
                user=user_profile.user,
                amount=bet.bet_size,
                type=1,
                from_wallet=user_profile.crypto_wallet_address,
                to_wallet=APP_WALLET,
                block=get_current_or_create_open_block(),
                bet=bet,
            )
        except:
            bet.is_active = False
            bet.save()


def recreate_bets(bets: list[Bet]):
    for bet in bets:
        Bet.objects.create(
            user=bet.user,
            bet_size=bet.bet_size,
            bet_percent=bet.bet_percent,
            start_matter_price=float(get_token_priceBCS(MATTER_TOKEN_ADDRESS)),
            start_idea_price=float(get_token_priceBCS(IDEA_TOKEN_ADDRESS)),
            is_active=bet.is_active,
            is_winning=bet.is_winning,
            bet_ratio=bet.bet_ratio,
        )
        bet.soft_delete()


def close_block(block: Block) -> Block:
    block.state = 0
    block.save()
    return block


def create_open_block_if_does_not_exist() -> Block:
    return get_current_or_create_open_block()


def main():
    N = 1
    M = 0.001

    open_block = get_open_block()
    frozen_block = freeze_block(open_block)

    bets = get_bets()
    winning_bets, loosing_bets = determine_winning_and_loosing_bets(bets)
    process_winning_bets(winning_bets)
    process_loosing_bets(loosing_bets)

    try:
        add_liquidity(
            APP_WALLET_PRIVATE_KEY, IDEA_TOKEN_ADDRESS, N, MATTER_TOKEN_ADDRESS, M
        )
        with open("./bet_manager.log", "a") as log_file:
            log_file.write(
                f"Sent addLiquidity transaction at {datetime.now().ctime()}\n"
            )
    except:
        with open("./bet_manager.log", "a") as log_file:
            log_file.write(
                f"Need more BNB on app wallet to send addLiquidity transaction at {datetime.now().ctime()}\n"
            )

    bets = get_bets()
    recreate_bets(bets)

    close_block(frozen_block)
    create_open_block_if_does_not_exist()


def scheduled_main(scheduler: sched.scheduler):
    scheduler.enter(BLOCK_REFRESH_PERIOD, 1, scheduled_main, (scheduler,))
    with open("./bet_manager.log", "a") as log_file:
        log_file.write(f"Started bet_manager at {datetime.now().ctime()}\n")
    with open("./next_block_sync.txt", "w") as file:
        file.write(str(int(time.time() * 1000) + BLOCK_REFRESH_PERIOD * 1000))
    try:
        main()
    except Exception as err:
        print(f"[ERROR] {err}")
        with open("./bet_manager.log", "a") as log_file:
            log_file.write(
                f"Bet manager failed at {datetime.now().ctime()} with error:\n[ERROR] {err}\n"
            )


if __name__ == "__main__":
    s = sched.scheduler(time.time, time.sleep)
    s.enter(0, 1, scheduled_main, (s,))
    s.run()
