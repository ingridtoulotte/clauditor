"""Check plugins.

Each module in this package exposes:
    NAME: str
    run(rules, sources, ctx) -> list[Finding]

To add your own check, drop a new module here and add it to
``clauditor.registry.CHECK_MODULES``. That's the whole extension contract.
"""
