"""Fabrique un petit PNG valide pour tester l'envoi d'un logo, sans fichier réel."""

import struct
import zlib


def png_minimal(largeur=40, hauteur=20):
    def bloc(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))

    brut = b"".join(b"\x00" + b"\x20\x80\xc0" * largeur for _ in range(hauteur))
    return (
        b"\x89PNG\r\n\x1a\n"
        + bloc(b"IHDR", struct.pack(">IIBBBBB", largeur, hauteur, 8, 2, 0, 0, 0))
        + bloc(b"IDAT", zlib.compress(brut))
        + bloc(b"IEND", b"")
    )
