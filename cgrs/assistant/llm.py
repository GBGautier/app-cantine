"""Appel d'un modèle de langage par une clé API gratuite (Gemini, Mistral ou Groq : API compatible « OpenAI »).

Aucune bibliothèque ajoutée : requêtes HTTPS avec la bibliothèque standard. La clé n'est jamais journalisée.
"""

import json
import urllib.error
import urllib.request

from cgrs import db

PROVIDERS = {
    "gemini": {
        "nom": "Google Gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "modele": "gemini-2.5-flash",
        "cle": "https://aistudio.google.com/apikey",
    },
    "mistral": {
        "nom": "Mistral",
        "url": "https://api.mistral.ai/v1/chat/completions",
        "modele": "mistral-small-latest",
        "cle": "https://console.mistral.ai/api-keys",
    },
    "groq": {
        "nom": "Groq",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "modele": "llama-3.3-70b-versatile",
        "cle": "https://console.groq.com/keys",
    },
}
TIMEOUT = 90


class ErreurModele(Exception):
    """Erreur lisible renvoyée par le fournisseur du modèle (clé refusée, quota atteint, …)."""


def _setting(cle):
    r = db.one("SELECT value FROM settings WHERE key=?", (cle,))
    return (r["value"] if r else "") or ""


def lire_config():
    """Réglages enregistrés : {fournisseur, modele, cle} (chaînes vides si non renseignés)."""
    return {
        "fournisseur": _setting("assistant_provider"),
        "modele": _setting("assistant_model"),
        "cle": _setting("assistant_key"),
    }


def est_configure():
    c = lire_config()
    return bool(c["fournisseur"] in PROVIDERS and c["cle"])


def appeler(messages, outils=None):
    """Une réponse du modèle (message « assistant » au format OpenAI : content, tool_calls)."""
    c = lire_config()
    p = PROVIDERS.get(c["fournisseur"])
    if not p or not c["cle"]:
        raise ErreurModele("L'assistant n'est pas configuré (Paramètres > Assistant IA).")
    corps = {"model": c["modele"] or p["modele"], "messages": messages, "temperature": 0.3}
    if outils:
        corps["tools"] = [
            {"type": "function", "function": {"name": o.nom, "description": o.description, "parameters": o.schema}}
            for o in outils
        ]
        corps["tool_choice"] = "auto"
    req = urllib.request.Request(
        p["url"],
        data=json.dumps(corps).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + c["cle"],
            "User-Agent": "cantine-assistant/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode(errors="replace")[:300]
        except Exception:
            pass
        if e.code in (401, 403):
            raise ErreurModele(
                f"Clé API refusée par {p['nom']} : vérifiez-la dans Paramètres > Assistant IA."
            ) from None
        if e.code == 429:
            raise ErreurModele(f"Quota gratuit de {p['nom']} atteint : réessayez dans quelques instants.") from None
        raise ErreurModele(f"{p['nom']} a répondu une erreur {e.code}. {detail}".strip()) from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ErreurModele(f"{p['nom']} est injoignable ({getattr(e, 'reason', e)}).") from None
    except ValueError:
        raise ErreurModele(f"Réponse illisible de {p['nom']}.") from None
    try:
        msg = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        raise ErreurModele(f"Réponse inattendue de {p['nom']}.") from None
    appels = []
    for i, tc in enumerate(msg.get("tool_calls") or []):
        f = tc.get("function") or {}
        appels.append(
            {
                "id": tc.get("id") or f"appel_{i + 1}",
                "type": "function",
                "function": {"name": f.get("name") or "", "arguments": f.get("arguments") or "{}"},
            }
        )
    out = {"role": "assistant", "content": msg.get("content") if isinstance(msg.get("content"), str) else ""}
    if appels:
        out["tool_calls"] = appels
    return out
