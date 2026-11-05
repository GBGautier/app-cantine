"""Appel d'un modèle de langage par une clé API gratuite (Gemini, Mistral ou Groq : API compatible « OpenAI »).

Aucune bibliothèque ajoutée : requêtes HTTPS avec la bibliothèque standard. La clé n'est jamais journalisée.
"""

import json
import os
import re
import time
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

    def __init__(self, message, code=None, sans_outils=False, appel_invalide=False):
        super().__init__(message)
        self.code = code  # code HTTP du fournisseur, s'il y en a un
        self.sans_outils = sans_outils  # le modèle ne gère pas les appels d'outils
        self.appel_invalide = appel_invalide  # le modèle a inventé un outil ou des arguments invalides


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


def _message_fournisseur(corps):
    """Texte d'erreur d'une réponse du fournisseur (JSON {error: {message}} ou liste de ces objets), coupé."""
    try:
        d = json.loads(corps)
        d = d[0] if isinstance(d, list) and d else d
        m = d["error"]["message"] if isinstance(d, dict) and isinstance(d.get("error"), dict) else None
        if m:
            return str(m).strip()[:200]
    except (ValueError, KeyError, TypeError, IndexError):
        pass
    return re.sub(r"\s+", " ", corps).strip()[:200]


PASSAGERES = (500, 502, 503, 504)  # erreurs temporaires du fournisseur : on réessaie
PAUSES = (1.5, 4)  # secondes d'attente avant chaque nouvelle tentative


def _attente_quota(e, detail):
    """Secondes à attendre avant de réessayer après un 429, si c'est court (≤ 10 s) ; sinon None."""
    try:
        v = float(e.headers.get("retry-after")) if e.headers and e.headers.get("retry-after") else None
    except (TypeError, ValueError):
        v = None
    if v is None:
        m = re.search(r"try again in (?:(\d+)m)?(\d+(?:\.\d+)?)s", detail or "", re.I)
        v = (int(m.group(1) or 0) * 60 + float(m.group(2))) if m else None
    return min(v + 0.5, 10) if v is not None and v <= 10 else None


def _requete(req, p, modele=""):
    """Envoie la requête ; rend le JSON de la réponse ou lève ErreurModele (messages lisibles, sans la clé)."""
    for essai in range(len(PAUSES) + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = _message_fournisseur(e.read().decode(errors="replace"))
            except Exception:
                pass
            if e.code in PASSAGERES and essai < len(PAUSES):
                time.sleep(PAUSES[essai])
                continue
            if e.code in (401, 403):
                raise ErreurModele(
                    f"Clé API refusée par {p['nom']} : vérifiez-la dans Paramètres > Assistant IA.", e.code
                ) from None
            if e.code == 404:
                raise ErreurModele(
                    f"Modèle « {modele} » introuvable chez {p['nom']} : choisissez-en un dans la liste (Paramètres > Assistant IA).",
                    404,
                ) from None
            if e.code == 429:
                attente = _attente_quota(e, detail)
                if attente is not None and essai < len(PAUSES):
                    time.sleep(attente)  # limite par minute : une courte attente suffit
                    continue
                raise ErreurModele(
                    f"Quota gratuit de {p['nom']} atteint ({detail or 'trop de requêtes'}). "
                    "Réessayez dans une minute, ou choisissez un autre modèle (Paramètres > Assistant IA).",
                    429,
                ) from None
            if e.code in PASSAGERES:
                raise ErreurModele(
                    f"{p['nom']} est surchargé en ce moment ({detail or 'erreur ' + str(e.code)}). Réessayez dans un instant, "
                    "ou choisissez un autre modèle (Paramètres > Assistant IA).",
                    e.code,
                ) from None
            if e.code == 400 and re.search(
                r"tool call validation|not in request\.tools|failed_generation", detail, re.I
            ):
                raise ErreurModele(
                    f"Le modèle « {modele} » a mal formulé un appel d'outil. Reformulez votre demande, "
                    "ou choisissez un autre modèle (Paramètres > Assistant IA).",
                    400,
                    appel_invalide=True,
                ) from None
            if (
                e.code == 400
                and re.search(r"tool.?(calling|use)|function.?call", detail, re.I)
                and "thought_signature" not in detail
            ):
                raise ErreurModele(
                    f"Le modèle « {modele} » ne gère pas les appels d'outils : choisissez-en un autre (Paramètres > Assistant IA).",
                    400,
                    sans_outils=True,
                ) from None
            raise ErreurModele(f"{p['nom']} a répondu une erreur {e.code} : {detail}".strip(" :"), e.code) from None
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


def _rang_gemini(i):
    """Tri des modèles Gemini : « flash » stables récents d'abord, puis « flash-lite », puis les autres."""
    m = re.search(r"gemini-(\d+(?:\.\d+)?)", i)
    version = float(m.group(1)) if m else 0.0
    famille = 2 if "flash" not in i else (1 if "lite" in i else 0)
    instable = 1 if re.search(r"preview|exp|\d{3}$|latest", i) else 0
    return (famille, instable, -version, i)


def lister_modeles(fournisseur, cle):
    """Modèles de conversation disponibles pour cette clé (identifiants, le plus adapté en premier)."""
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
    if fournisseur == "groq":  # sans appels d'outils : inutilisables par l'assistant
        ids = {i for i in ids if not re.search(r"gemma|allam|compound|orpheus|prompt", i, re.I)}
    if fournisseur == "gemini":
        ids = sorted(ids, key=_rang_gemini)
    elif fournisseur == "groq":
        ids = sorted(ids, key=lambda i: (0 if "llama" in i.lower() else 1, i))
    else:
        ids = sorted(ids)
    reco = recommander(fournisseur, ids)
    return ([reco] if reco else []) + [i for i in ids if i != reco]


def oublier_modele_auto():
    _cache_auto.clear()


def _candidats(c, p):
    """Modèles à essayer, dans l'ordre : celui choisi (seul), sinon les mieux classés parmi ceux que la clé permet d'utiliser."""
    if c["modele"]:
        return [c["modele"]], False
    cle = (c["fournisseur"], c["cle"][-8:])
    if cle not in _cache_auto:
        try:
            _cache_auto[cle] = lister_modeles(c["fournisseur"], c["cle"])[:4] or [p["modele"]]
        except ErreurModele:
            return [p["modele"]], True  # la liste est indisponible : on tente le modèle par défaut
    return list(_cache_auto[cle]), True


def appeler(messages, outils=None):
    """Une réponse du modèle (message « assistant » au format OpenAI : content, tool_calls).

    Modèle choisi : utilisé tel quel. Mode automatique : si un modèle est introuvable ou surchargé, le suivant est essayé,
    et celui qui répond passe en tête pour les messages suivants.
    """
    c = lire_config()
    p = PROVIDERS.get(c["fournisseur"])
    if not p or not c["cle"]:
        raise ErreurModele("L'assistant n'est pas configuré (Paramètres > Assistant IA).")
    candidats, auto = _candidats(c, p)
    corps = {"messages": messages, "temperature": 0.3}
    if outils:
        corps["tools"] = [
            {"type": "function", "function": {"name": o.nom, "description": o.description, "parameters": o.schema}}
            for o in outils
        ]
        corps["tool_choice"] = "auto"
    data = None
    for rang, modele in enumerate(candidats):
        corps["model"] = modele
        corps["temperature"] = 0.3
        req = urllib.request.Request(
            _url_chat(p),
            data=json.dumps(corps).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + c["cle"],
                "User-Agent": "cantine-assistant/1.0",
            },
        )
        try:
            try:
                data = _requete(req, p, modele)
            except ErreurModele as e:
                if not e.appel_invalide:
                    raise
                # le modèle a inventé un outil : un second essai, plus déterministe, suffit le plus souvent
                corps["temperature"] = 0
                req.data = json.dumps(corps).encode()
                data = _requete(req, p, modele)
        except ErreurModele as e:
            if (
                auto
                and rang + 1 < len(candidats)
                and (e.code in (404, *PASSAGERES) or e.sans_outils or e.appel_invalide)
            ):
                continue
            raise
        if auto and rang:
            _cache_auto[(c["fournisseur"], c["cle"][-8:])] = [modele] + [m for m in candidats if m != modele]
        break
    try:
        msg = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        raise ErreurModele(f"Réponse inattendue de {p['nom']}.") from None
    appels = []
    for i, tc in enumerate(msg.get("tool_calls") or []):
        f = tc.get("function") or {}
        appel = {
            "id": tc.get("id") or f"appel_{i + 1}",
            "type": "function",
            "function": {"name": f.get("name") or "", "arguments": f.get("arguments") or "{}"},
        }
        if isinstance(tc.get("extra_content"), dict):  # Gemini 3 : signature de réflexion à renvoyer telle quelle
            appel["extra_content"] = tc["extra_content"]
        appels.append(appel)
    out = {"role": "assistant", "content": msg.get("content") if isinstance(msg.get("content"), str) else ""}
    if appels:
        out["tool_calls"] = appels
    return out
