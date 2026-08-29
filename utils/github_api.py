"""
CORTEX — En-têtes pour l'API GitHub.

Sans jeton, l'API de recherche GitHub n'accepte que 10 requêtes par minute :
les scouts (viral, signaux faibles, outils) en font une quinzaine en parallèle
et se prennent des 403. Dans GitHub Actions, GITHUB_TOKEN est fourni
gratuitement et fait passer la limite à 30/min.
"""

import os


def github_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers
