"""Serveur MCP (Model Context Protocol), transport « Streamable HTTP » sans état : un POST JSON-RPC, une réponse JSON.

Méthodes gérées : initialize, ping, tools/list, tools/call (et les notifications, acquittées sans réponse).
"""

from cgrs.assistant import outils
from cgrs.assistant.outils import ErreurOutil

VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
INSTRUCTIONS = (
    "Outils de gestion d'une cantine scolaire : produits, fournisseurs, stock, recettes, repas, réceptions, statistiques. "
    "Cherchez les produits existants (rechercher_produits) avant de créer une recette ou une réception ; "
    "les montants sont en euros HT, les quantités en kg, l ou unités."
)


def _erreur(id_, code, message):
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def _liste(role):
    return [
        {
            "name": o.nom,
            "title": o.titre,
            "description": o.description,
            "inputSchema": o.schema,
            "annotations": {"readOnlyHint": not o.ecriture, "destructiveHint": False, "openWorldHint": False},
        }
        for o in outils.outils_permis(role)
    ]


def traiter(msg, user):
    """Traite un message JSON-RPC ; rend la réponse (dict) ou None pour une notification."""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
        return _erreur(None, -32600, "Requête JSON-RPC invalide")
    methode = msg.get("method")
    if methode is None:  # réponse du client à une requête du serveur : rien à faire
        return None
    if "id" not in msg:  # notification (ex. notifications/initialized)
        return None
    id_, params = msg["id"], msg.get("params") or {}
    if methode == "initialize":
        demande = params.get("protocolVersion")
        return {
            "jsonrpc": "2.0",
            "id": id_,
            "result": {
                "protocolVersion": demande if demande in VERSIONS else VERSIONS[0],
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "cantine", "title": "Gestion de cantine", "version": "1.0"},
                "instructions": INSTRUCTIONS,
            },
        }
    if methode == "ping":
        return {"jsonrpc": "2.0", "id": id_, "result": {}}
    if methode == "tools/list":
        return {"jsonrpc": "2.0", "id": id_, "result": {"tools": _liste(user["role"])}}
    if methode == "tools/call":
        nom = params.get("name")
        if nom not in outils.PAR_NOM:
            return _erreur(id_, -32602, f"Outil inconnu : {nom}")
        try:
            texte, erreur = outils.en_texte(outils.executer(user, nom, params.get("arguments") or {})), False
        except ErreurOutil as e:
            texte, erreur = str(e), True
        return {
            "jsonrpc": "2.0",
            "id": id_,
            "result": {"content": [{"type": "text", "text": texte}], "isError": erreur},
        }
    return _erreur(id_, -32601, f"Méthode inconnue : {methode}")
