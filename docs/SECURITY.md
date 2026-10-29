# Sécurité - CGRS - Réceptions & stocks

## Table des matières

1. [Politique de sécurité](#politique-de-sécurité)
2. [Vulnérabilités connues](#vulnérabilités-connues)
3. [Configuration de sécurité](#configuration-de-sécurité)
4. [Authentification](#authentification)
5. [Protection des données](#protection-des-données)
6. [Sécurité du réseau](#sécurité-du-réseau)
7. [Bonnes pratiques](#bonnes-pratiques)
8. [Audit de sécurité](#audit-de-sécurité)
9. [Gestion des incidents](#gestion-des-incidents)
10. [Checklist de sécurité](#checklist-de-sécurité)

---

## Politique de sécurité

### Engagement

Nous nous engageons à maintenir un niveau élevé de sécurité pour l'application CGRS. La sécurité est une priorité absolue, et nous prenons les mesures nécessaires pour protéger les données de nos utilisateurs.

### Signalement des vulnérabilités

Si vous découvrez une vulnérabilité de sécurité, merci de nous la signaler de manière responsable :

1. **Ne pas divulguer publiquement** la vulnérabilité
2. **Envoyer un email** à : [security@cgrs.fr](mailto:security@cgrs.fr)
3. **Inclure** les informations suivantes :
   - Description de la vulnérabilité
   - Étapes pour la reproduire
   - Impact potentiel
   - Solution proposée (si disponible)

Nous nous engageons à :
- Accuser réception de votre rapport dans les 24 heures
- Traiter le rapport de manière confidentielle
- Corriger la vulnérabilité dans les meilleurs délais
- Vous informer de la résolution
- Optionnellement, vous créditer dans les remerciements (si vous le souhaitez)

---

## Vulnérabilités connues

Aucune vulnérabilité connue à ce jour.

---

## Configuration de sécurité

### Variables d'environnement sensibles

Les variables suivantes doivent être configurées avec soin :

| Variable | Description | Recommandation |
|----------|-------------|----------------|
| `SECRET_KEY` | Clé secrète pour les sessions | 32+ caractères aléatoires |
| `DATABASE_PATH` | Chemin de la base de données | Répertoire sécurisé |
| `UPLOADS_DIR` | Répertoire des uploads | Répertoire sécurisé, pas accessible publiquement |
| `BACKUPS_DIR` | Répertoire des sauvegardes | Répertoire sécurisé |
| `CORS_ORIGINS` | Origines CORS autorisées | Limiter aux domaines de confiance |
| `HTTPS_MODE` | Activer HTTPS | `true` en production |
| `CSRF_PROTECTION` | Protection CSRF | `true` (activé par défaut) |

### Génération d'une clé secrète

```python
import secrets
print(secrets.token_urlsafe(32))
```

### Configuration recommandée pour la production

```ini
# .env
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=votre-cle-secrete-aleatoire-de-32-caracteres-minimum
CORS_ORIGINS=https://votre-domaine.com
HTTPS_MODE=true
CSRF_PROTECTION=true
MAX_UPLOAD_SIZE=25
MAX_LOGIN_ATTEMPTS=5
LOGIN_LOCKOUT_DURATION=300  # 5 minutes
```

---

## Authentification

### Hachage des mots de passe

- **Algorithme** : PBKDF2-SHA256
- **Itérations** : 240 000 (configurable)
- **Sel** : 16 octets aléatoires
- **Longueur du hash** : 64 octets

**Pourquoi PBKDF2 ?**
- Résistant aux attaques par force brute
- Conçu pour le hachage des mots de passe
- Recommandé par OWASP

### Gestion des sessions

- **Tokens de session** : 32 caractères aléatoires (URL-safe)
- **Durée** : 30 jours (configurable)
- **Stockage** : Hash SHA-256 dans la base de données
- **Cookies** :
  - `HttpOnly` : Empêche l'accès via JavaScript
  - `SameSite=Lax` : Protection CSRF
  - `Secure` : HTTPS uniquement (en production)
  - `Path=/` : Accessible sur tout le site

### Protection contre les attaques par force brute

- **Limite des tentatives** : 5 tentatives maximum
- **Durée de blocage** : 60 secondes (configurable)
- **Clé de blocage** : Basée sur l'IP + nom d'utilisateur

### Rôles et permissions

| Rôle | Description | Permissions |
|------|-------------|-------------|
| `admin` | Administrateur | Tous les droits |
| `editor` | Éditeur | Lecture et modification |
| `reader` | Lecteur | Lecture seule |
| `stats` | Statistiques | Accès aux statistiques (prix masqués) |

---

## Protection des données

### Chiffrement

- **En transit** : HTTPS (TLS 1.2+) recommandé
- **Au repos** : Les données sensibles (mots de passe) sont hachées
- **Sauvegardes** : Doivent être stockées de manière sécurisée

### Données sensibles

| Donnée | Stockage | Protection |
|--------|----------|------------|
| Mots de passe | Base de données | Hachage PBKDF2-SHA256 |
| Tokens de session | Base de données | Hash SHA-256 |
| Noms d'utilisateur | Base de données | Texte clair |
| Données des fournisseurs | Base de données | Texte clair |
| Données des produits | Base de données | Texte clair |
| Fichiers uploadés | Système de fichiers | Répertoire sécurisé |

### Nettoyage des entrées utilisateur

Toutes les entrées utilisateur doivent être :

1. **Validées** : Vérifier le format et les contraintes
2. **Sanitisées** : Nettoyer les caractères dangereux
3. **Échappées** : Éviter les injections SQL (via les paramètres)

Exemple de validation avec Pydantic :

```python
from pydantic import BaseModel, Field, constr

class UserCreate(BaseModel):
    username: constr(min_length=3, max_length=40, regex=r"^[a-z0-9._@-]+$")
    password: constr(min_length=8)
    email: str = Field(..., regex=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
```

### Protection contre les injections SQL

Toujours utiliser les **paramètres** pour les requêtes SQL :

```python
# Bon
def get_user(user_id: int):
    return one("SELECT * FROM users WHERE id=?", (user_id,))

# Mauvais (NE JAMAIS FAIRE)
def get_user(user_id: int):
    return one(f"SELECT * FROM users WHERE id={user_id}")
```

---

## Sécurité du réseau

### Protection CORS

- **Origines autorisées** : Configurables via `CORS_ORIGINS`
- **Méthodes autorisées** : Toutes (GET, POST, PUT, DELETE, etc.)
- **En-têtes autorisés** : Tous
- **Credentials** : Autorisées

Configuration recommandée :

```python
CORS_ORIGINS = "https://votre-domaine.com,https://www.votre-domaine.com"
```

### Protection CSRF

- **En-tête requis** : `x-requested-with: cgrs`
- **Méthodes concernées** : POST, PUT, DELETE, PATCH
- **Activation** : Toujours activée (configurable via `CSRF_PROTECTION`)

Exemple de requête avec protection CSRF :

```javascript
fetch("/api/users", {
    method: "POST",
    headers: {
        "Content-Type": "application/json",
        "x-requested-with": "cgrs"
    },
    body: JSON.stringify({ username: "test", password: "test123" })
})
```

### En-têtes de sécurité HTTP

Les en-têtes suivants sont ajoutés automatiquement :

| En-tête | Valeur | Description |
|---------|--------|-------------|
| `X-Content-Type-Options` | `nosniff` | Empêche le MIME sniffing |
| `X-Frame-Options` | `DENY` | Empêche l'affichage dans une iframe |
| `Referrer-Policy` | `same-origin` | Limite les informations du referrer |
| `Cache-Control` | `no-store` | Désactive le cache pour les endpoints API |

### Sécurité des uploads

- **Extensions autorisées** : `.pdf`, `.png`, `.jpg`, `.jpeg`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.odt`, `.ods`, `.txt`
- **Taille maximale** : 25 Mo (configurable)
- **Stockage** : Répertoire dédié, pas accessible publiquement
- **Nom des fichiers** : Générés aléatoirement pour éviter les conflits

Exemple de gestion des uploads :

```python
ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx", ".xls", ".xlsx", ".odt", ".ods", ".txt"}
MAX_UPLOAD = 25 * 1024 * 1024

async def save_upload(file: UploadFile) -> str:
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "Type de fichier non autorisé")
    
    # Générer un nom de fichier sécurisé
    name = f"{secrets.token_hex(6)}_{file.filename}"
    dest = UPLOADS_DIR / name
    
    # Limiter la taille
    size = 0
    with dest.open("wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD:
                raise HTTPException(413, "Fichier trop volumineux")
            f.write(chunk)
    
    return name
```

---

## Bonnes pratiques

### Développement

1. **Ne jamais committer de secrets** :
   - Ne pas mettre de mots de passe ou clés dans le code
   - Utiliser les variables d'environnement
   - Ajouter les fichiers sensibles dans `.gitignore`

2. **Valider toutes les entrées** :
   - Utiliser Pydantic pour la validation
   - Vérifier les contraintes (longueur, format, etc.)
   - Nettoyer les données avant utilisation

3. **Utiliser des requêtes paramétrées** :
   - Toujours utiliser `?` pour les paramètres SQL
   - Ne jamais concaténer les valeurs directement

4. **Limiter les permissions** :
   - Donner le minimum de permissions nécessaires
   - Vérifier les rôles avant les actions sensibles

5. **Journaliser les actions** :
   - Journaliser les actions sensibles (création, modification, suppression)
   - Ne pas journaliser les données sensibles (mots de passe, etc.)

### Déploiement

1. **Utiliser HTTPS** :
   - Toujours activer HTTPS en production
   - Utiliser TLS 1.2 ou supérieur
   - Configurer les certificats SSL valides

2. **Sécuriser le serveur** :
   - Mettre à jour régulièrement le système
   - Installer un pare-feu
   - Désactiver les services inutiles

3. **Protéger les répertoires** :
   - Limiter l'accès aux répertoires sensibles
   - Désactiver l'exécution de scripts dans les répertoires d'upload
   - Configurer les permissions correctement

4. **Sauvegarder régulièrement** :
   - Sauvegarder la base de données
   - Sauvegarder les fichiers uploadés
   - Tester les restaurations

5. **Monitorer les logs** :
   - Surveiller les tentatives de connexion échouées
   - Détecter les activités suspectes
   - Configurer des alertes

---

## Audit de sécurité

### Outils recommandés

| Outil | Description | Commande |
|-------|-------------|----------|
| `safety` | Vérification des vulnérabilités des dépendances | `safety check` |
| `bandit` | Analyse statique de code Python | `bandit -r src/` |
| `pylint` | Linting avancé | `pylint src/` |
| `trivy` | Scanner de conteneurs | `trivy image cgrs-app` |
| `nmap` | Scan de ports | `nmap localhost` |
| `sqlmap` | Test d'injections SQL | `sqlmap -u http://localhost:8000 --risk=3 --level=5` |

### Vérifications manuelles

1. **Vérifier les permissions** :
   ```bash
   # Vérifier les permissions des fichiers
   ls -la
   
   # Vérifier les permissions des répertoires
   ls -ld data/ uploads/
   ```

2. **Vérifier les ports ouverts** :
   ```bash
   netstat -tuln
   ss -tuln
   ```

3. **Vérifier les processus en cours** :
   ```bash
   ps aux | grep python
   top
   ```

4. **Vérifier les logs** :
   ```bash
   # Logs de l'application
   tail -f logs/*.log
   
   # Logs système
   journalctl -u cgrs-app
   ```

---

## Gestion des incidents

### Procédure en cas de faille de sécurité

1. **Isoler le système** :
   - Désactiver l'accès public
   - Déconnecter le système du réseau si nécessaire

2. **Évaluer l'impact** :
   - Identifier les données exposées
   - Identifier les systèmes affectés
   - Évaluer la gravité

3. **Corriger la faille** :
   - Appliquer les correctifs nécessaires
   - Mettre à jour les configurations
   - Redémarrer les services

4. **Investiguer** :
   - Analyser les logs
   - Identifier la cause racine
   - Documenter l'incident

5. **Communiquer** :
   - Informer les parties concernées
   - Rédiger un rapport d'incident
   - Proposer des actions correctives

6. **Améliorer** :
   - Mettre à jour les procédures
   - Renforcer les mesures de sécurité
   - Former le personnel

---

## Checklist de sécurité

### Avant le déploiement

- [ ] Tous les secrets sont dans des variables d'environnement
- [ ] HTTPS est activé
- [ ] Les en-têtes de sécurité sont configurés
- [ ] La protection CSRF est activée
- [ ] La protection CORS est configurée
- [ ] Les permissions des fichiers sont correctes
- [ ] Les sauvegardes sont configurées
- [ ] Le monitoring est en place
- [ ] Les logs sont configurés
- [ ] Les tests de sécurité ont été exécutés

### Après le déploiement

- [ ] Le système est à jour
- [ ] Les pare-feux sont configurés
- [ ] Les sauvegardes fonctionnent
- [ ] Le monitoring est actif
- [ ] Les alertes sont configurées
- [ ] La documentation est à jour
- [ ] Le personnel est formé

### Maintenance régulière

- [ ] Mettre à jour le système régulièrement
- [ ] Mettre à jour les dépendances
- [ ] Vérifier les vulnérabilités
- [ ] Tester les sauvegardes
- [ ] Revoir les permissions
- [ ] Analyser les logs
- [ ] Effectuer des audits de sécurité

---

## Ressources

### Documentation

- [OWASP Top 10](https://owasp.org/www-project-top-ten/) : Top 10 des vulnérabilités web
- [OWASP Cheat Sheets](https://cheatsheetseries.owasp.org/) : Bonnes pratiques de sécurité
- [CWE Top 25](https://cwe.mitre.org/top25/) : Top 25 des erreurs de programmation
- [Python Security](https://wiki.python.org/moin/Security) : Sécurité Python

### Outils

- [Safety](https://github.com/pyupio/safety) : Vérification des vulnérabilités
- [Bandit](https://github.com/PyCQA/bandit) : Analyse statique de sécurité
- [Trivy](https://github.com/aquasecurity/trivy) : Scanner de conteneurs
- [Nmap](https://nmap.org/) : Scanner de réseau
- [SQLMap](https://sqlmap.org/) : Test d'injections SQL

### Formations

- [OWASP Web Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/) : Guide de test de sécurité
- [PortSwigger Academy](https://portswigger.net/web-security) : Formation en sécurité web
- [Hack The Box](https://www.hackthebox.com/) : Plateforme de pratique

---

## Contact

Pour toute question ou préoccupation concernant la sécurité :

- **Email** : [security@cgrs.fr](mailto:security@cgrs.fr)
- **Téléphone** : +33 1 23 45 67 89
- **Adresse** : 123 Rue de la Sécurité, 75000 Paris, France

---

*Dernière mise à jour : Octobre 2026*
