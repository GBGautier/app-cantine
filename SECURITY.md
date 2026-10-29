# Politique de sécurité

## Signalement des vulnérabilités

Si vous découvrez une vulnérabilité de sécurité dans ce projet, merci de la signaler de manière responsable en suivant ces étapes :

1. **Ne pas divulguer publiquement** la vulnérabilité
2. **Envoyer un email** à l'adresse appropriée (si disponible)
3. **Fournir les détails** : description, étapes de reproduction, impact, solution suggérée

Nous nous engageons à traiter les rapports de vulnérabilités de manière rapide et confidentielle.

## Bonnes pratiques de sécurité

### Pour les développeurs

- Ne jamais committer de secrets (mots de passe, clés API, etc.) dans le code
- Utiliser des variables d'environnement pour les informations sensibles
- Valider et sanitizer toutes les entrées utilisateur
- Utiliser des requêtes SQL paramétrées pour éviter les injections
- Limiter les permissions selon le principe du moindre privilège

### Pour les utilisateurs

- Utiliser des mots de passe forts (8+ caractères, mélange de types)
- Activer la protection CSRF dans la configuration
- Limiter les origines CORS autorisées
- Configurer HTTPS en production
- Sauvegarder régulièrement les données

## Configuration de sécurité recommandée

```ini
# .env
SECRET_KEY=votre-cle-secrete-aleatoire-de-32-caracteres-minimum
CSRF_PROTECTION=true
CORS_ORIGINS=https://votre-domaine.com
HTTPS_MODE=true
MAX_LOGIN_ATTEMPTS=5
LOGIN_LOCKOUT_DURATION=300
```

## Outils de sécurité

- **safety** : Vérification des vulnérabilités des dépendances Python
- **bandit** : Analyse statique de code pour détecter les problèmes de sécurité
- **trivy** : Scanner de conteneurs pour détecter les vulnérabilités

## Ressources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/) - Top 10 des vulnérabilités web
- [OWASP Cheat Sheets](https://cheatsheetseries.owasp.org/) - Bonnes pratiques de sécurité
- [Python Security](https://wiki.python.org/moin/Security) - Documentation sécurité Python
