# Bibliothèques tierces embarquées

Elles sont servies par l'application elle-même (aucun accès à Internet n'est nécessaire, et leur contenu ne peut pas
changer sans modification du dépôt).

| Fichier | Bibliothèque | Version | Licence | Usage |
|---|---|---|---|---|
| `jspdf-2.5.1.umd.min.js` | [jsPDF](https://github.com/parallax/jsPDF) | 2.5.1 | MIT (`jspdf.LICENSE`) | exports PDF (statistiques, liste de courses) |
| `jspdf-autotable-3.8.2.min.js` | [jsPDF-AutoTable](https://github.com/simonbengtsson/jsPDF-AutoTable) | 3.8.2 | MIT (`jspdf-autotable.LICENSE.txt`) | tableaux dans les PDF |

Empreintes SHA-256 :

```
98ccf17aa10c20bb1301762618fcc9b6ab3a4e7f26b6071d64d0b41154df3875  jspdf-2.5.1.umd.min.js
27a9c3b61843c6312b87f142d40fe77c0f0f054c9f3cdeccc4bfd5f3322859c8  jspdf-autotable-3.8.2.min.js
```

Origine : paquets officiels npm `jspdf@2.5.1` et `jspdf-autotable@3.8.2` (dossier `dist/`).

Mettre à jour : `npm pack jspdf@X jspdf-autotable@Y`, remplacer les fichiers, mettre à jour ce tableau et les deux lignes
`<script>` de `static/index.html`, puis lancer `pytest tests/ui` (un test génère un PDF hors ligne).
