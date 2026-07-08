from __future__ import annotations

import json
import sys
from pathlib import Path

from coding_agent.store import SqliteStore


def main() -> int:
    db_path = Path(sys.argv[1])
    run_id = sys.argv[2]
    store = SqliteStore(db_path)
    print(json.dumps(store.list_events(run_id), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
