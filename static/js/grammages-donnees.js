/* ---------- Grammages flat list (module-level for recipeForm access) ---------- */
const GRAMMAGES_DATA = {
  entrees: {
    label: 'Entrées',
    sections: [
      {
        title: null,
        rows: [
          {label: 'Pain', gemrcn: ['30', '40', '50 à 100'], cgrs: ['30', '40', '50'], coeff: 1},
        ]
      },
      {
        title: 'Crudités sans assaisonnement',
        rows: [
          {label: 'Avocat', gemrcn: ['50', '70', '80 à 100'], cgrs: ['50', '70', '90'], coeff: 1},
          {label: 'Carottes, céleri et autres racines râpées', gemrcn: ['50', '70', '90 à 120'], cgrs: ['50', '70', '105'], coeff: 1},
          {label: 'Choux rouges et choux blanc émincé', gemrcn: ['40', '60', '80 à 100'], cgrs: ['40', '60', '90'], coeff: 1},
          {label: 'Concombre', gemrcn: ['60', '80', '90 à 100'], cgrs: ['60', '80', '95'], coeff: 1},
          {label: 'Endive', gemrcn: ['20', '30', '80 à 100'], cgrs: ['20', '30', '90'], coeff: 1},
          {label: 'Melon, Pastèque', gemrcn: ['120', '150', '150 à 200'], cgrs: ['120', '150', '175'], coeff: 1},
          {label: 'Pamplemousse (à l\'unité ou segments)', gemrcn: ['1/2', '1/2', '1/2'], cgrs: ['1/2', '1/2', '1'], coeff: 1, unit: 'unité'},
          {label: 'Radis', gemrcn: ['30', '50', '80 à 100'], cgrs: ['30', '50', '90'], coeff: 1},
          {label: 'Salade verte', gemrcn: ['25', '30', '40 à 60'], cgrs: ['25', '30', '50'], coeff: 1},
          {label: 'Tomate', gemrcn: ['60', '80', '100 à 120'], cgrs: ['60', '80', '110'], coeff: 1},
          {label: 'Salade composée à base de crudités', gemrcn: ['40', '60', '80 à 100'], cgrs: ['40', '60', '90'], coeff: 1},
          {label: 'Champignons crus', gemrcn: ['40', '60', '80 à 100'], cgrs: ['40', '60', '90'], coeff: 1},
          {label: 'Fenouil', gemrcn: ['40', '60', '80 à 100'], cgrs: ['40', '60', '90'], coeff: 1},
        ]
      },
      {
        title: 'Cuidités sans assaisonnement',
        rows: [
          {label: 'Potage à base de légumes', gemrcn: ['0,125 l', '0,167 l', '0,250 l'], cgrs: ['0,125 l', '0,167 l', '0,250 l'], coeff: 1},
          {label: 'Artichaut entier (à l\'unité)', gemrcn: ['1/2', '1/2', '1'], cgrs: ['1/2', '1/2', '1'], coeff: 1, unit: 'unité'},
          {label: 'Fond d\'artichaut', gemrcn: ['50', '70', '80 à 100'], cgrs: ['50', '70', '90'], coeff: 1},
          {label: 'Asperges', gemrcn: ['50', '70', '80 à 100'], cgrs: ['50', '70', '90'], coeff: 1},
          {label: 'Betteraves', gemrcn: ['50', '70', '90 à 120'], cgrs: ['50', '70', '105'], coeff: 1},
          {label: 'Céleri', gemrcn: ['50', '70', '90 à 120'], cgrs: ['50', '70', '105'], coeff: 1},
          {label: 'Champignons', gemrcn: ['50', '70', '100 à 120'], cgrs: ['50', '70', '110'], coeff: 1},
          {label: 'Choux-fleurs', gemrcn: ['50', '70', '90 à 120'], cgrs: ['50', '70', '105'], coeff: 1},
          {label: 'Cœurs de palmier', gemrcn: ['40', '60', '80 à 100'], cgrs: ['40', '60', '90'], coeff: 1},
          {label: 'Fenouil', gemrcn: ['40', '60', '80 à 100'], cgrs: ['40', '60', '90'], coeff: 1},
          {label: 'Haricots verts', gemrcn: ['50', '70', '90 à 120'], cgrs: ['50', '70', '105'], coeff: 1},
          {label: 'Poireaux (blancs de poireaux)', gemrcn: ['50', '70', '90 à 120'], cgrs: ['50', '70', '105'], coeff: 1},
          {label: 'Salade composée à base de légumes cuits', gemrcn: ['50', '70', '90 à 120'], cgrs: ['50', '70', '105'], coeff: 1},
          {label: 'Soja (germes de haricots mungo)', gemrcn: ['50', '70', '90 à 120'], cgrs: ['50', '70', '105'], coeff: 1},
          {label: 'Terrine de légumes', gemrcn: ['30', '30', '30 à 50'], cgrs: ['30', '30', '40'], coeff: 1},
        ]
      },
      {
        title: 'Entrées de féculents (salades composées à base de pommes de terre, blé, riz, semoule ou pâtes)',
        rows: [
          {label: 'Féculents (salade composée)', gemrcn: ['60', '80', '100 à 150'], cgrs: ['60', '80', '125'], coeff: 1},
        ]
      },
      {
        title: 'Entrées protidiques diverses',
        rows: [
          {label: 'Œuf dur (à l\'unité)', gemrcn: ['1/2', '1', '1 à 1,5'], cgrs: ['1/2', '1', '1'], coeff: 1, unit: 'unité'},
          {label: 'Hareng', gemrcn: ['30', '40', '40 à 60'], cgrs: ['30', '40', '50'], coeff: 1},
          {label: 'Maquereau', gemrcn: ['30', '30', '40 à 50'], cgrs: ['30', '30', '45'], coeff: 1},
          {label: 'Sardines (à l\'unité)', gemrcn: ['1', '1', '2'], cgrs: ['1', '1', '2'], coeff: 1, unit: 'unité'},
          {label: 'Thon au naturel', gemrcn: ['30', '30', '40 à 50'], cgrs: ['30', '30', '45'], coeff: 1},
          {label: 'Surimi', gemrcn: ['30', '30', '40 à 50'], cgrs: ['30', '30', '45'], coeff: 1},
          {label: 'Jambon cru de pays', gemrcn: ['20', '30', '40 à 50'], cgrs: ['20', '30', '45'], coeff: 1},
          {label: 'Jambon blanc', gemrcn: ['30', '40', '50'], cgrs: ['30', '40', '50'], coeff: 1},
          {label: 'Pâté, terrine, mousse', gemrcn: ['30', '30', '30 à 50'], cgrs: ['30', '30', '40'], coeff: 1},
          {label: 'Pâté en croûte', gemrcn: ['45', '45', '65'], cgrs: ['45', '45', '65'], coeff: 1},
          {label: 'Rillettes', gemrcn: ['30', '30', '30 à 50'], cgrs: ['30', '30', '40'], coeff: 1},
          {label: 'Salami – Saucisson – Mortadelle', gemrcn: ['30', '30', '40 à 50'], cgrs: ['30', '30', '45'], coeff: 1},
        ]
      },
      {
        title: 'Entrées de préparations pâtissières salées',
        rows: [
          {label: 'Nems', gemrcn: ['50', '50', '100'], cgrs: ['50', '50', '100'], coeff: 1},
          {label: 'Crêpes', gemrcn: ['50', '50', '100'], cgrs: ['50', '50', '100'], coeff: 1},
          {label: 'Friand, feuilleté', gemrcn: ['55 à 70', '55 à 70', '80 à 120'], cgrs: ['60', '60', '100'], coeff: 1},
          {label: 'Pizza', gemrcn: ['70', '70', '90'], cgrs: ['70', '70', '90'], coeff: 1},
          {label: 'Tarte salée', gemrcn: ['70', '70', '90'], cgrs: ['70', '70', '90'], coeff: 1},
        ]
      },
      {
        title: 'Assaisonnement hors-d\'œuvre',
        rows: [
          {label: 'Assaisonnement (poids matière grasse)', gemrcn: ['5', '7', '8'], cgrs: ['5', '7', '8'], coeff: 1},
        ]
      },
    ]
  },
  plats: {
    label: 'Plats + Accompagnements',
    sections: [
      {
        title: 'Bœuf',
        rows: [
          {label: 'Bœuf braisé, bœuf sauté, bouilli de bœuf', gemrcn: ['50', '70', '100 à 120'], cgrs: ['50', '70', '110'], coeff: 1.33},
          {label: 'Rôti de bœuf, steak', gemrcn: ['40', '60', '80 à 100'], cgrs: ['40', '60', '90'], coeff: 1.33},
          {label: 'Steak haché de bœuf, viande hachée de bœuf', gemrcn: ['50', '70', '100'], cgrs: ['50', '70', '100'], coeff: 1.25},
          {label: 'Hamburger de bœuf, autre préparation de viande de bœuf hachée', gemrcn: ['50', '70', '100'], cgrs: ['50', '70', '100'], coeff: 1},
          {label: 'Boulettes de bœuf de 30 g pièce crues (à l\'unité)', gemrcn: ['2', '3', '4 à 5'], cgrs: ['2', '3', '4'], coeff: 1, unit: 'unité'},
        ]
      },
      {
        title: 'Veau',
        rows: [
          {label: 'Sauté de veau ou blanquette (sans os)', gemrcn: ['50', '70', '100 à 120'], cgrs: ['50', '70', '110'], coeff: 1.25},
          {label: 'Escalope de veau, rôti de veau', gemrcn: ['40', '60', '80 à 100'], cgrs: ['40', '60', '90'], coeff: 1.33},
          {label: 'Steak haché de veau, viande hachée de veau', gemrcn: ['50', '70', '80 à 100'], cgrs: ['50', '70', '90'], coeff: 1.25},
          {label: 'Hamburger de veau, Rissolette, préparation de viande de veau hachée', gemrcn: ['50', '70', '100'], cgrs: ['50', '70', '100'], coeff: 1},
          {label: 'Paupiette de veau', gemrcn: ['50', '70', '100 à 120'], cgrs: ['50', '70', '110'], coeff: 1.25},
        ]
      },
      {
        title: 'Agneau – Mouton',
        rows: [
          {label: 'Gigot', gemrcn: ['40', '60', '80 à 100'], cgrs: ['40', '60', '90'], coeff: 1.33},
          {label: 'Sauté (sans os)', gemrcn: ['50', '70', '100 à 120'], cgrs: ['50', '70', '110'], coeff: 1.25},
          {label: 'Côte d\'agneau avec os', gemrcn: ['—', '80', '100 à 120'], cgrs: ['—', '80', '110'], coeff: 1.33},
          {label: 'Boulettes d\'agneau-mouton de 30 g pièce crues (à l\'unité)', gemrcn: ['2', '3', '4 à 5'], cgrs: ['2', '3', '4'], coeff: 1, unit: 'unité'},
          {label: 'Merguez de 50 g pièce crues (à l\'unité)', gemrcn: ['1', '2', '2 à 3'], cgrs: ['1', '2', '2'], coeff: 1, unit: 'unité'},
        ]
      },
      {
        title: 'Porc',
        rows: [
          {label: 'Rôti de porc, grillade (sans os)', gemrcn: ['40', '60', '80 à 100'], cgrs: ['40', '60', '90'], coeff: 1.33},
          {label: 'Sauté (sans os)', gemrcn: ['50', '70', '100 à 120'], cgrs: ['50', '70', '110'], coeff: 1.25},
          {label: 'Côte de porc (avec os)', gemrcn: ['—', '80', '100 à 120'], cgrs: ['—', '80', '110'], coeff: 1.33},
          {label: 'Jambon DD, palette de porc', gemrcn: ['40', '60', '80 à 100'], cgrs: ['40', '60', '90'], coeff: 1.25},
          {label: 'Andouillettes', gemrcn: ['50', '70', '100 à 120'], cgrs: ['50', '70', '110'], coeff: 1},
          {label: 'Saucisse de porc de 50 g pièce crue (à l\'unité)', gemrcn: ['1', '2', '2 à 3'], cgrs: ['1', '2', '2'], coeff: 1, unit: 'unité'},
        ]
      },
      {
        title: 'Volaille – Lapin',
        rows: [
          {label: 'Rôti, escalope et aiguillettes de volaille, blanc de poulet', gemrcn: ['40', '60', '80 à 100'], cgrs: ['40', '60', '90'], coeff: 1.33},
          {label: 'Sauté et émincé de volaille', gemrcn: ['50', '70', '100 à 120'], cgrs: ['50', '70', '110'], coeff: 1.25},
          {label: 'Jambon de volaille', gemrcn: ['40', '60', '80 à 100'], cgrs: ['40', '60', '90'], coeff: 1},
          {label: 'Cordon bleu ou pané façon cordon bleu', gemrcn: ['50', '70', '100 à 120'], cgrs: ['50', '70', '110'], coeff: 1},
          {label: 'Cuisse, haut de cuisse, pilon de volaille (avec os)', gemrcn: ['100', '140', '140 à 180'], cgrs: ['100', '140', '160'], coeff: 1.33},
          {label: 'Brochette', gemrcn: ['50', '70', '100 à 120'], cgrs: ['50', '70', '110'], coeff: 1.33},
          {label: 'Paupiette de volaille', gemrcn: ['50', '70', '100 à 120'], cgrs: ['50', '70', '110'], coeff: 1.25},
          {label: 'Fingers, beignets, nuggets de 20 g pièce cuits (à l\'unité)', gemrcn: ['2', '3', '5'], cgrs: ['2', '3', '5'], coeff: 1, unit: 'unité'},
          {label: 'Escalope panée de volaille ou autre viande', gemrcn: ['50', '70', '100 à 120'], cgrs: ['50', '70', '110'], coeff: 1},
          {label: 'Cuisse ou demi-cuisse de lapin (avec os)', gemrcn: ['100', '140', '140 à 180'], cgrs: ['100', '140', '160'], coeff: 1.33},
          {label: 'Sauté et émincé de lapin (sans os)', gemrcn: ['50', '70', '100 à 120'], cgrs: ['50', '70', '110'], coeff: 1.25},
          {label: 'Paupiette de lapin', gemrcn: ['50', '70', '100 à 120'], cgrs: ['50', '70', '110'], coeff: 1.25},
          {label: 'Saucisse de volaille de 50 g pièce crue (à l\'unité)', gemrcn: ['1', '2', '2 à 3'], cgrs: ['1', '2', '2'], coeff: 1, unit: 'unité'},
        ]
      },
      {
        title: 'Abats',
        rows: [
          {label: 'Foie, langue, rognons, boudin', gemrcn: ['50', '70', '100 à 120'], cgrs: ['50', '70', '110'], coeff: 1},
          {label: 'Tripes avec sauce', gemrcn: ['50', '70', '100 à 200'], cgrs: ['50', '70', '110'], coeff: 1},
        ]
      },
      {
        title: 'Œufs (plat principal)',
        rows: [
          {label: 'Œufs durs (à l\'unité)', gemrcn: ['1', '2', '2 à 3'], cgrs: ['1', '2', '2'], coeff: 1, unit: 'unité'},
          {label: 'Omelette', gemrcn: ['60', '90', '90 à 130'], cgrs: ['60', '90', '110'], coeff: 1},
        ]
      },
      {
        title: 'Poissons (sans sauce)',
        rows: [
          {label: 'Poissons non enrobés sans arêtes (filets, rôtis, steaks, brochettes, cubes)', gemrcn: ['50', '70', '100 à 120'], cgrs: ['50', '70', '110'], coeff: 1.25},
          {label: 'Brochettes de poisson', gemrcn: ['50', '70', '100 à 120'], cgrs: ['50', '70', '110'], coeff: 1.25},
          {label: 'Darne', gemrcn: ['—', '—', '120 à 140'], cgrs: ['—', '—', '130'], coeff: 1.25},
          {label: 'Beignets, poissons panés ou enrobés (croquettes, paupiettes…)', gemrcn: ['50', '70', '100 à 120'], cgrs: ['50', '70', '110'], coeff: 1},
          {label: 'Poissons entiers', gemrcn: ['—', '—', '150 à 170'], cgrs: ['—', '—', '160'], coeff: 1.25},
        ]
      },
      {
        title: 'Plats composés',
        rows: [
          {label: 'Denrée protidique du plat composé (choucroute, paëlla, hachis, brandade, légumes farcis, raviolis, cannellonis, lasagnes…)', gemrcn: ['50', '70', '100 à 120'], cgrs: ['50', '70', '110'], coeff: 1.25},
          {label: 'Portion de plat composé (denrée protidique + garniture + sauce)', gemrcn: ['180', '250', '250 à 300'], cgrs: ['180', '250', '275'], coeff: 1},
          {label: 'Préparations pâtissières en plat principal (crêpes, pizzas, croque monsieur, friands, quiches…)', gemrcn: ['100', '150', '200'], cgrs: ['100', '150', '200'], coeff: 1.1},
          {label: 'Quenelle', gemrcn: ['60', '80', '120 à 160'], cgrs: ['60', '80', '140'], coeff: 1},
        ]
      },
      {
        title: 'Légumes cuits',
        rows: [
          {label: 'Légumes cuits (accompagnement)', gemrcn: ['100', '100', '150'], cgrs: ['100', '100', '150'], coeff: 1},
        ]
      },
      {
        title: 'Féculents cuits',
        rows: [
          {label: 'Riz', gemrcn: ['120', '170', '200 à 250'], cgrs: ['120', '170', '225'], coeff: 0.4},
          {label: 'Pâtes', gemrcn: ['120', '170', '200 à 250'], cgrs: ['120', '170', '225'], coeff: 0.36},
          {label: 'Pommes de terre', gemrcn: ['120', '170', '200 à 250'], cgrs: ['120', '170', '225'], coeff: 1},
          {label: 'Purée de pomme de terre (fraîche ou reconstituée)', gemrcn: ['150', '200', '250'], cgrs: ['150', '200', '250'], coeff: 1},
          {label: 'Frites', gemrcn: ['120', '170', '200 à 250'], cgrs: ['120', '170', '225'], coeff: 1},
          {label: 'Chips', gemrcn: ['30', '30', '60'], cgrs: ['30', '30', '60'], coeff: 1},
          {label: 'Légumes secs', gemrcn: ['120', '170', '200 à 250'], cgrs: ['120', '170', '225'], coeff: 0.37},
        ]
      },
      {
        title: 'Sauces pour plats',
        rows: [
          {label: 'Sauces (jus de viande, sauce tomate, béchamel, beurre blanc, mayonnaise, ketchup…) – poids matière grasse', gemrcn: ['5', '7', '8'], cgrs: ['5', '7', '8'], coeff: 1},
        ]
      },
    ]
  },
  fromages: {
    label: 'Fromages',
    sections: [
      {
        title: null,
        rows: [
          {label: 'Fromages', gemrcn: ['16 à 20', '16 à 30', '16 à 40'], cgrs: ['18', '23', '28'], coeff: 1},
        ]
      }
    ]
  },
  desserts: {
    label: 'Desserts + Laitages',
    sections: [
      {
        title: 'Laitages',
        rows: [
          {label: 'Fromage blanc, fromages frais', gemrcn: ['90 à 120', '90 à 120', '90 à 120'], cgrs: ['105', '105', '105'], coeff: 1},
          {label: 'Yaourt et autres laits fermentés', gemrcn: ['100 à 125', '100 à 125', '100 à 125'], cgrs: ['110', '110', '110'], coeff: 1},
          {label: 'Petit suisse et autres fromages frais de type suisse', gemrcn: ['50 à 60', '50 à 60', '100 à 120'], cgrs: ['55', '55', '110'], coeff: 1},
          {label: 'Lait demi-écrémé (menus 4 composantes)', gemrcn: ['125 ml', '125 ml', '250 ml'], cgrs: ['125 ml', '125 ml', '250 ml'], coeff: 1},
        ]
      },
      {
        title: 'Desserts',
        rows: [
          {label: 'Desserts lactés', gemrcn: ['90 à 125', '90 à 125', '90 à 125'], cgrs: ['105', '105', '105'], coeff: 1},
          {label: 'Mousse', gemrcn: ['10 à 12 cl', '10 à 12 cl', '10 à 12 cl'], cgrs: ['11 cl', '11 cl', '11 cl'], coeff: 1},
          {label: 'Fruits crus', gemrcn: ['100', '100', '100 à 150'], cgrs: ['100', '100', '125'], coeff: 1},
          {label: 'Fruits cuits', gemrcn: ['100', '100', '100 à 150'], cgrs: ['100', '100', '125'], coeff: 1},
          {label: 'Fruits secs', gemrcn: ['20', '20', '30'], cgrs: ['20', '20', '30'], coeff: 1},
          {label: 'Pâtisseries à base de pâte à choux (en portions ou à découper)', gemrcn: ['20 à 45', '20 à 45', '40 à 60'], cgrs: ['32', '32', '50'], coeff: 1},
          {label: 'Pâtisseries fraîches, surgelées ou déshydratées (en portions ou à découper)', gemrcn: ['40 à 60', '40 à 60', '60 à 80'], cgrs: ['50', '50', '70'], coeff: 1},
          {label: 'Pâtisserie sèche emballée (biscuits et gâteaux à température ambiante)', gemrcn: ['20 à 30', '20 à 30', '30 à 50'], cgrs: ['25', '25', '40'], coeff: 1},
          {label: 'Biscuits d\'accompagnement', gemrcn: ['15', '15', '20'], cgrs: ['15', '15', '20'], coeff: 1},
          {label: 'Glaces et sorbets', gemrcn: ['50 à 70 ml', '50 à 100 ml', '50 à 150 ml'], cgrs: ['60 ml', '75 ml', '100 ml'], coeff: 1},
          {label: 'Desserts contenant plus de 60 % de fruits', gemrcn: ['80 à 100', '80 à 100', '80 à 100'], cgrs: ['90', '90', '90'], coeff: 1},
        ]
      },
    ]
  },
};
const GRAM_UNIT_RE = /à l'unité/;

function gramRowsFromData(data) {
  // Aplatit les données structurées en liste de lignes complètes : {label, gemrcn, cgrs, coeff, unit, section_*}
  const rows = [];
  for (const [sk, tab] of Object.entries(data)) {
    for (const sec of tab.sections) {
      for (const row of sec.rows) {
        rows.push({
          section_key: sk, section_label: tab.label, section_title: sec.title || null,
          label: row.label, gemrcn: row.gemrcn || [], cgrs: row.cgrs,
          coeff: row.coeff != null ? row.coeff : 1,
          unit: row.unit || (GRAM_UNIT_RE.test(row.label) ? 'unité' : null),
        });
      }
    }
  }
  // surcharges éventuelles non encore migrées en base
  for (const r of rows) {
    const ov = GRAM_OVERRIDES[r.label];
    if (ov) {
      if (Array.isArray(ov.cgrs)) r.cgrs = ov.cgrs.slice();
      if (ov.coeff != null) r.coeff = ov.coeff;
    }
  }
  return rows;
}

let GRAM_ROWS = null;   // grammages chargés depuis la base de données

async function loadGramRows() {
  if (GRAM_ROWS) return GRAM_ROWS;
  await loadGramOverrides();
  const builtin = gramRowsFromData(GRAMMAGES_DATA);
  try {
    const rows = await api('/grammages-rows');
    if (Array.isArray(rows) && rows.length) { GRAM_ROWS = rows; return GRAM_ROWS; }
    // Premier lancement : la base est vide, on y enregistre les valeurs par défaut
    GRAM_ROWS = builtin;
    api('/grammages-rows', {method: 'PUT', body: {rows: builtin.map(r => ({...r}))}}).catch(() => {});
  } catch (e) { GRAM_ROWS = builtin; }
  return GRAM_ROWS;
}

function getGrammageRows() {
  return GRAM_ROWS || gramRowsFromData(GRAMMAGES_DATA);
}

// Cache global des surcharges de grammages, indexé par libellé : {[label]: {cgrs, coeff}}
let CONVIVES_DEF = {mat: 140, elem: 240, adu: 5};
let GRAM_OVERRIDES = {};
async function loadGramOverrides() {
  try { GRAM_OVERRIDES = (await api('/grammages')) || {}; } catch (e) { GRAM_OVERRIDES = {}; }
  return GRAM_OVERRIDES;
}

function parseCgrsValGlobal(s) {
  if (!s || s === '—') return null;
  const str = String(s).trim().replace(',', '.');
  const vol = str.match(/^(\d+(?:\.\d+)?)\s*(ml|cl|l)$/i);
  if (vol) {
    const n = parseFloat(vol[1]);
    const u = vol[2].toLowerCase();
    const factor = u === 'ml' ? 0.001 : u === 'cl' ? 0.01 : 1;
    return n * factor; // litres
  }
  if (/[a-zA-Z]/.test(str)) return null;
  const frac = str.match(/^(\d+(?:\.\d+)?)\/(\d+(?:\.\d+)?)$/);
  if (frac) return parseFloat(frac[1]) / parseFloat(frac[2]);
  const n = parseFloat(str);
  return isNaN(n) ? null : n;
}

