"""`dota-sensei` command line entry point.

    dota-sensei serve                 # dev API on 8273
    dota-sensei sync 70388657 -n 20   # pull matches and run the analysis
    dota-sensei rules                 # list registered mistake detectors
"""

import argparse
import asyncio

from app.analysis import REGISTRY
from app.config import get_settings
from app.db import SessionLocal
from app.services.ingest import sync_player


async def _sync(account_id: int, limit: int) -> None:
    async with SessionLocal() as session:
        result = await sync_player(session, account_id, limit)
        await session.commit()
    print(
        f"account {result.account_id}: saw {result.matches_seen} matches, "
        f"ingested {result.matches_ingested}, created {result.insights_created} insights"
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="dota-sensei")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("serve", help="run the dev API server")
    sub.add_parser("rules", help="list registered analysis rules")

    sync_cmd = sub.add_parser("sync", help="ingest recent matches for an account")
    sync_cmd.add_argument("account_id", type=int, nargs="?")
    sync_cmd.add_argument("-n", "--limit", type=int, default=20)

    args = parser.parse_args()

    if args.command == "serve":
        from app.main import main as serve

        serve()
    elif args.command == "rules":
        for key in sorted(REGISTRY):
            print(key)
    elif args.command == "sync":
        account_id = args.account_id or get_settings().default_account_id
        if account_id is None:
            parser.error("pass an account_id or set DOTA_SENSEI_DEFAULT_ACCOUNT_ID")
        asyncio.run(_sync(account_id, args.limit))


if __name__ == "__main__":
    main()
