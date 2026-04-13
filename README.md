# CORTEX — Système Multi-Agents de Veille Sectorielle

Surveille 4 secteurs (IA, Crypto/Web3, Marchés, DeepTech) pour détecter des signaux faibles et viraux.
Envoie un rapport complet chaque matin à 6h sur Telegram.

## Structure

```
autonomous/
  agents/          # Agents intelligents (Phase 2)
  database/        # Client Supabase + schema
  telegram/        # Bot Telegram
  utils/           # Logger
  main.py          # Point d'entrée
  scheduler.py     # Tâches planifiées
```

## Démarrage rapide

```bash
pip install -r requirements.txt
python main.py
```

## Phases

- **Phase 1** (actuelle) : Infrastructure + squelette + scheduler
- **Phase 2** : Agents SCOUT collectent les signaux
- **Phase 3** : SHERLOCK analyse avec Claude API
- **Phase 4** : NEXUS génère les rapports complets
