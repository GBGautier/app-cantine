# Bibliothèques tierces embarquées

Elles sont servies par l'application elle-même (aucun accès à Internet n'est nécessaire, et leur contenu ne peut pas
changer sans modification du dépôt).

| Fichier | Bibliothèque | Version | Licence | Usage |
|---|---|---|---|---|
| `jspdf-4.2.1.umd.min.js` | [jsPDF](https://github.com/parallax/jsPDF) | 4.2.1 | MIT (`jspdf.LICENSE`) | exports PDF (statistiques, liste de courses) |
| `jspdf-autotable-5.0.9.min.js` | [jsPDF-AutoTable](https://github.com/simonbengtsson/jsPDF-AutoTable) | 5.0.9 | MIT (`jspdf-autotable.LICENSE.txt`) | tableaux dans les PDF |

Empreintes SHA-256 :

```
e6551fcdc32f09d6853b2c5126d18d01d9447e0da618a41a11ebeee0f6c20d54  jspdf-4.2.1.umd.min.js
83dd8e5ae29436bd3d3ef4f4a915125b3951264994c25de0359d3fbd105abe15  jspdf-autotable-5.0.9.min.js
```

Origine : paquets officiels npm `jspdf@4.2.1` et `jspdf-autotable@5.0.9` (dossier `dist/`).

Mettre à jour : `npm pack jspdf@X jspdf-autotable@Y`, remplacer les fichiers, mettre à jour ce tableau et les deux lignes
`<script>` de `static/index.html`, puis lancer `pytest tests/ui` (un test génère un PDF hors ligne).
