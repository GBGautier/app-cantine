"""Appel d'un modèle de langage par une clé API gratuite (Gemini, Mistral ou Groq : API compatible « OpenAI »).

Aucune bibliothèque ajoutée : requêtes HTTPS avec la bibliothèque standard. La clé n'est jamais journalisée.
"""

import json
import os
import re
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


def _url_chat(p):
    # CGRS_ASSISTANT_URL : adresse d'un serveur compatible « OpenAI » de votre choix (modèle local, passerelle, tests)
    return os.environ.get("CGRS_ASSISTANT_URL") or p["url"]


def _url_modeles(p):
    base = _url_chat(p)
    return (
        base[: -len("/chat/completions")] if base.endswith("/chat/completions") else base.rsplit("/", 1)[0]
    ) + "/models"


def _requete(req, p, modele=""):
    """Envoie la requête ; rend le JSON de la réponse ou lève ErreurModele (messages lisibles, sans la clé)."""
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode())
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
        if e.code == 404:
            raise ErreurModele(
                f"Modèle « {modele} » introuvable chez {p['nom']} : choisissez-en un dans la liste (Paramètres > Assistant IA)."
            ) from None
        if e.code == 429:
            raise ErreurModele(f"Quota gratuit de {p['nom']} atteint : réessayez dans quelques instants.") from None
        raise ErreurModele(f"{p['nom']} a répondu une erreur {e.code}. {detail}".strip()) from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ErreurModele(f"{p['nom']} est injoignable ({getattr(e, 'reason', e)}).") from None
    except ValueError:
        raise ErreurModele(f"Réponse illisible de {p['nom']}.") from None


# Modèles qui ne répondent pas à une conversation (vectorisation, voix, image, modération…)
_EXCLUS = re.compile(
    r"embed|whisper|tts|guard|moderat|ocr|transcri|imag|veo|aqa|audio|live|tuning|robotics|speech|playai|rerank|safeguard|"
    r"computer-use|deep-research",
    re.I,
)
_cache_auto: dict = {}


def recommander(fournisseur, ids):
    """Le modèle le plus adapté parmi ceux proposés (gratuit et rapide, avec appels d'outils) ; '' si la liste est vide."""
    if not ids:
        return ""
    if fournisseur == "gemini":
        flash = []
        for i in ids:
            m = re.fullmatch(r"gemini-(\d+(?:\.\d+)?)-flash(-latest)?", i)
            if m:
                flash.append((float(m.group(1)), not m.group(2), i))
        if flash:
            return max(flash)[2]
        autres = [i for i in ids if "flash" in i and "lite" not in i]
        return sorted(autres)[-1] if autres else ids[0]
    if fournisseur == "mistral":
        return next((i for i in ("mistral-small-latest", "mistral-medium-latest") if i in ids), ids[0])
    return next((i for i in ("llama-3.3-70b-versatile",) if i in ids), next((i for i in ids if "70b" in i), ids[0]))


def lister_modeles(fournisseur, cle):
    """Modèles de conversation disponibles pour cette clé (identifiants, le recommandé en premier)."""
    p = PROVIDERS.get(fournisseur)
    if not p:
        raise ErreurModele("Fournisseur inconnu.")
    req = urllib.request.Request(
        _url_modeles(p), headers={"Authorization": "Bearer " + cle, "User-Agent": "cantine-assistant/1.0"}
    )
    data = _requete(req, p)
    ids = set()
    for m in (data.get("data") if isinstance(data, dict) else None) or []:
        i = re.sub(r"^models/", "", str((m or {}).get("id") or ""))
        if i and not _EXCLUS.search(i) and (fournisseur != "gemini" or i.startswith("gemini")):
            ids.add(i)
    ids = sorted(ids)
    reco = recommander(fournisseur, ids)
    return ([reco] if reco else []) + [i for i in ids if i != reco]


def oublier_modele_auto():
    _cache_auto.clear()


def _modele_effectif(c, p):
    """Modèle choisi, sinon le recommandé parmi ceux que la clé permet d'utiliser (repli : modèle par défaut)."""
    if c["modele"]:
        return c["modele"]
    cle = (c["fournisseur"], c["cle"][-8:])
    if cle not in _cache_auto:
        try:
            _cache_auto[cle] = (lister_modeles(c["fournisseur"], c["cle"]) or [p["modele"]])[0]
        except ErreurModele:
            return p["modele"]  # la liste est indisponible : on tente le modèle par défaut
    return _cache_auto[cle]


def appeler(messages, outils=None):
    """Une réponse du modèle (message « assistant » au format OpenAI : content, tool_calls)."""
    c = lire_config()
    p = PROVIDERS.get(c["fournisseur"])
    if not p or not c["cle"]:
        raise ErreurModele("L'assistant n'est pas configuré (Paramètres > Assistant IA).")
    corps = {"model": _modele_effectif(c, p), "messages": messages, "temperature": 0.3}
    if outils:
        corps["tools"] = [
            {"type": "function", "function": {"name": o.nom, "description": o.description, "parameters": o.schema}}
            for o in outils
        ]
        corps["tool_choice"] = "auto"
    req = urllib.request.Request(
        _url_chat(p),
        data=json.dumps(corps).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + c["cle"],
            "User-Agent": "cantine-assistant/1.0",
        },
    )
    data = _requete(req, p, corps["model"])
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
