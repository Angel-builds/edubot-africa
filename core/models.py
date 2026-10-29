"""List the models the configured key can actually serve.

    python -m core.models

Worth having because a model id is the one piece of configuration that cannot
be checked offline. Fireworks retires serverless models, and the error you get
for a dead id does not say so -- it reads like a malformed request.
"""

from __future__ import annotations

import sys

from core import llm


def fireworks() -> list[str]:
    import os

    import httpx2

    response = httpx2.get(
        f"{llm.FIREWORKS_URL}/models",
        headers={"Authorization": f"Bearer {os.environ['FIREWORKS_API_KEY']}"},
        timeout=llm.TIMEOUT,
    )
    response.raise_for_status()
    return sorted(entry["id"] for entry in response.json().get("data", []))


def anthropic() -> list[str]:
    import anthropic as sdk

    return sorted(m.id for m in sdk.Anthropic().models.list(limit=50).data)


def main() -> None:
    name = llm.provider()
    if not name:
        keys = ", ".join(spec["key"] for spec in llm.PROVIDERS.values())
        sys.exit(f"No API key set. Set one of: {keys}")

    listers = {"fireworks": fireworks, "anthropic": anthropic}
    ids = listers[name]()

    print(f"{name}: {len(ids)} models this key can reach\n")
    for model_id in ids:
        marker = " <- EDUBOT_MODEL" if model_id == llm.model() else ""
        print(f"  {model_id}{marker}")

    if llm.model() not in ids:
        print(
            f"\n  warning: the configured model {llm.model()!r} is not in that list.\n"
            f"  Pick one above and set EDUBOT_MODEL."
        )


if __name__ == "__main__":
    main()
