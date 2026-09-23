export interface ECUEResult {
  code: string;
  nom: string;
  note: number; // /20
  coef: number;
}

export interface UEResult {
  code: string;
  nom: string;
  ects: number;
  ecues: ECUEResult[];
  moyenneUE: number;
  validee: boolean;
  valideeParCompensation: boolean;
  hasNoteEliminatoire: boolean;
}

export interface EtudiantDeliberation {
  id: string;
  matricule: string;
  nom: string;
  prenom: string;
  filiere: string;
  semestre: string;
  ues: UEResult[];
  moyenneGenerale: number;
  totalECTSAcquis: number;
  totalECTSMax: number;
  statutSession: "Admis" | "Rattrapage" | "Ajourné";
  mention: "Très Bien" | "Bien" | "Assez Bien" | "Passable" | "Ajourné" | "Rattrapage";
  hasNoteEliminatoire: boolean;
  notesEliminatoiresDetails: string[];
}

export interface DeliberationConfig {
  seuilValidationMoyenne: number; // Default 10.0
  seuilEliminatoire: number; // Default 7.0 (any grade < 7 triggers failure/rattrapage)
  seuilPassageConditionnelECTS: number; // Default 18 ECTS out of 30
  compensationAutorisee: boolean; // Default true (inter-UE compensation if sem average >= 10)
}

export const DEFAULT_DELIBERATION_CONFIG: DeliberationConfig = {
  seuilValidationMoyenne: 10.0,
  seuilEliminatoire: 7.0,
  seuilPassageConditionnelECTS: 18,
  compensationAutorisee: true,
};

export const deliberationEngine = {
  // Calculer la délibération individuelle pour un étudiant
  calculerEtudiant: (
    etudiantRaw: {
      id: string;
      matricule: string;
      nom: string;
      prenom: string;
      filiere: string;
      semestre: string;
      uesRaw: {
        code: string;
        nom: string;
        ects: number;
        ecues: ECUEResult[];
      }[];
    },
    config: DeliberationConfig = DEFAULT_DELIBERATION_CONFIG
  ): EtudiantDeliberation => {
    let sumECTSValides = 0;
    let sumECTSWeighted = 0;
    let sumECTSTotal = 0;
    let globalHasEliminatoire = false;
    const allEliminatoires: string[] = [];

    // 1. Calcul des moyennes par UE
    const uesCalculees: UEResult[] = etudiantRaw.uesRaw.map((ue) => {
      const totalNoteCoef = ue.ecues.reduce((sum, e) => sum + e.note * e.coef, 0);
      const totalCoef = ue.ecues.reduce((sum, e) => sum + e.coef, 0);
      const moyenneUE = totalCoef > 0 ? Number((totalNoteCoef / totalCoef).toFixed(2)) : 0;

      // Check note éliminatoire dans l'UE
      const ueEliminatoires = ue.ecues.filter((e) => e.note < config.seuilEliminatoire);
      const hasNoteEliminatoire = ueEliminatoires.length > 0;

      if (hasNoteEliminatoire) {
        globalHasEliminatoire = true;
        ueEliminatoires.forEach((e) => {
          allEliminatoires.push(`${e.code} (${e.note}/20)`);
        });
      }

      sumECTSTotal += ue.ects;
      sumECTSWeighted += moyenneUE * ue.ects;

      return {
        code: ue.code,
        nom: ue.nom,
        ects: ue.ects,
        ecues: ue.ecues,
        moyenneUE,
        validee: moyenneUE >= config.seuilValidationMoyenne && !hasNoteEliminatoire,
        valideeParCompensation: false,
        hasNoteEliminatoire,
      };
    });

    // 2. Moyenne générale du semestre
    const moyenneGenerale =
      sumECTSTotal > 0 ? Number((sumECTSWeighted / sumECTSTotal).toFixed(2)) : 0;

    // 3. Application des règles de compensation
    const canCompensate =
      config.compensationAutorisee &&
      moyenneGenerale >= config.seuilValidationMoyenne &&
      !globalHasEliminatoire;

    uesCalculees.forEach((ue) => {
      if (ue.validee) {
        sumECTSValides += ue.ects;
      } else if (canCompensate && !ue.hasNoteEliminatoire) {
        ue.validee = true;
        ue.valideeParCompensation = true;
        sumECTSValides += ue.ects;
      }
    });

    // 4. Détermination automatique de la décision du jury
    let statutSession: EtudiantDeliberation["statutSession"] = "Ajourné";
    let mention: EtudiantDeliberation["mention"] = "Ajourné";

    if (moyenneGenerale >= config.seuilValidationMoyenne && sumECTSValides === sumECTSTotal) {
      statutSession = "Admis";
      if (moyenneGenerale >= 16) mention = "Très Bien";
      else if (moyenneGenerale >= 14) mention = "Bien";
      else if (moyenneGenerale >= 12) mention = "Assez Bien";
      else mention = "Passable";
    } else if (
      sumECTSValides >= config.seuilPassageConditionnelECTS ||
      globalHasEliminatoire ||
      (moyenneGenerale >= 8.5 && moyenneGenerale < config.seuilValidationMoyenne)
    ) {
      statutSession = "Rattrapage";
      mention = "Rattrapage";
    } else {
      statutSession = "Ajourné";
      mention = "Ajourné";
    }

    return {
      id: etudiantRaw.id,
      matricule: etudiantRaw.matricule,
      nom: etudiantRaw.nom,
      prenom: etudiantRaw.prenom,
      filiere: etudiantRaw.filiere,
      semestre: etudiantRaw.semestre,
      ues: uesCalculees,
      moyenneGenerale,
      totalECTSAcquis: sumECTSValides,
      totalECTSMax: sumECTSTotal,
      statutSession,
      mention,
      hasNoteEliminatoire: globalHasEliminatoire,
      notesEliminatoiresDetails: allEliminatoires,
    };
  },

  // Calculer toute une cohorte / promotion
  calculerPromotion: (
    etudiants: any[],
    config: DeliberationConfig = DEFAULT_DELIBERATION_CONFIG
  ): {
    resultats: EtudiantDeliberation[];
    stats: {
      total: number;
      admis: number;
      rattrapage: number;
      ajournes: number;
      tauxReussite: string;
      moyennePromo: string;
    };
  } => {
    const resultats = etudiants.map((e) => deliberationEngine.calculerEtudiant(e, config));

    const total = resultats.length;
    const admis = resultats.filter((r) => r.statutSession === "Admis").length;
    const rattrapage = resultats.filter((r) => r.statutSession === "Rattrapage").length;
    const ajournes = resultats.filter((r) => r.statutSession === "Ajourné").length;

    const sumMoyennes = resultats.reduce((acc, r) => acc + r.moyenneGenerale, 0);
    const moyennePromo = total > 0 ? (sumMoyennes / total).toFixed(2) : "0.00";
    const tauxReussite = total > 0 ? `${((admis / total) * 100).toFixed(1)}%` : "0%";

    return {
      resultats,
      stats: {
        total,
        admis,
        rattrapage,
        ajournes,
        tauxReussite,
        moyennePromo,
      },
    };
  },
};

export const MOCK_ETUDIANTS_PROMOTION = [
  {
    id: "etu-1",
    matricule: "ET2024001",
    nom: "Ba",
    prenom: "Amadou",
    filiere: "Master 1 Génie Logiciel",
    semestre: "Semestre 1",
    uesRaw: [
      {
        code: "UE-INF101",
        nom: "Architecture Logicielle & DevOps",
        ects: 10,
        ecues: [
          { code: "EC1", nom: "Microservices", note: 16.5, coef: 2 },
          { code: "EC2", nom: "Docker & Kubernetes", note: 15.0, coef: 2 },
        ],
      },
      {
        code: "UE-INF102",
        nom: "Ingénierie des Données & Cloud",
        ects: 10,
        ecues: [
          { code: "EC3", nom: "Bases NoSQL & Graph", note: 14.0, coef: 1.5 },
          { code: "EC4", nom: "Cloud Computing AWS", note: 15.5, coef: 1.5 },
        ],
      },
      {
        code: "UE-MGT101",
        nom: "Management Agile & Anglais Tech",
        ects: 10,
        ecues: [
          { code: "EC5", nom: "Scrum & Kanban", note: 17.0, coef: 1 },
          { code: "EC6", nom: "Anglais Professionnel", note: 14.5, coef: 1 },
        ],
      },
    ],
  },
  {
    id: "etu-2",
    matricule: "ET2024002",
    nom: "Sarr",
    prenom: "Fatou",
    filiere: "Master 1 Génie Logiciel",
    semestre: "Semestre 1",
    uesRaw: [
      {
        code: "UE-INF101",
        nom: "Architecture Logicielle & DevOps",
        ects: 10,
        ecues: [
          { code: "EC1", nom: "Microservices", note: 18.0, coef: 2 },
          { code: "EC2", nom: "Docker & Kubernetes", note: 17.5, coef: 2 },
        ],
      },
      {
        code: "UE-INF102",
        nom: "Ingénierie des Données & Cloud",
        ects: 10,
        ecues: [
          { code: "EC3", nom: "Bases NoSQL & Graph", note: 16.0, coef: 1.5 },
          { code: "EC4", nom: "Cloud Computing AWS", note: 16.5, coef: 1.5 },
        ],
      },
      {
        code: "UE-MGT101",
        nom: "Management Agile & Anglais Tech",
        ects: 10,
        ecues: [
          { code: "EC5", nom: "Scrum & Kanban", note: 15.0, coef: 1 },
          { code: "EC6", nom: "Anglais Professionnel", note: 18.0, coef: 1 },
        ],
      },
    ],
  },
  {
    id: "etu-3",
    matricule: "ET2024003",
    nom: "Diop",
    prenom: "Ibrahima",
    filiere: "Master 1 Génie Logiciel",
    semestre: "Semestre 1",
    uesRaw: [
      {
        code: "UE-INF101",
        nom: "Architecture Logicielle & DevOps",
        ects: 10,
        ecues: [
          { code: "EC1", nom: "Microservices", note: 8.0, coef: 2 },
          { code: "EC2", nom: "Docker & Kubernetes", note: 9.0, coef: 2 },
        ],
      },
      {
        code: "UE-INF102",
        nom: "Ingénierie des Données & Cloud",
        ects: 10,
        ecues: [
          { code: "EC3", nom: "Bases NoSQL & Graph", note: 12.0, coef: 1.5 },
          { code: "EC4", nom: "Cloud Computing AWS", note: 13.0, coef: 1.5 },
        ],
      },
      {
        code: "UE-MGT101",
        nom: "Management Agile & Anglais Tech",
        ects: 10,
        ecues: [
          { code: "EC5", nom: "Scrum & Kanban", note: 11.5, coef: 1 },
          { code: "EC6", nom: "Anglais Professionnel", note: 10.0, coef: 1 },
        ],
      },
    ],
  },
  {
    id: "etu-4",
    matricule: "ET2024004",
    nom: "Ndiaye",
    prenom: "Awa",
    filiere: "Master 1 Génie Logiciel",
    semestre: "Semestre 1",
    uesRaw: [
      {
        code: "UE-INF101",
        nom: "Architecture Logicielle & DevOps",
        ects: 10,
        ecues: [
          { code: "EC1", nom: "Microservices", note: 14.5, coef: 2 },
          { code: "EC2", nom: "Docker & Kubernetes", note: 13.0, coef: 2 },
        ],
      },
      {
        code: "UE-INF102",
        nom: "Ingénierie des Données & Cloud",
        ects: 10,
        ecues: [
          { code: "EC3", nom: "Bases NoSQL & Graph", note: 5.5, coef: 1.5 }, // Eliminatoire < 7
          { code: "EC4", nom: "Cloud Computing AWS", note: 14.0, coef: 1.5 },
        ],
      },
      {
        code: "UE-MGT101",
        nom: "Management Agile & Anglais Tech",
        ects: 10,
        ecues: [
          { code: "EC5", nom: "Scrum & Kanban", note: 13.0, coef: 1 },
          { code: "EC6", nom: "Anglais Professionnel", note: 12.0, coef: 1 },
        ],
      },
    ],
  },
  {
    id: "etu-5",
    matricule: "ET2024005",
    nom: "Traoré",
    prenom: "Mamadou",
    filiere: "Master 1 Génie Logiciel",
    semestre: "Semestre 1",
    uesRaw: [
      {
        code: "UE-INF101",
        nom: "Architecture Logicielle & DevOps",
        ects: 10,
        ecues: [
          { code: "EC1", nom: "Microservices", note: 6.0, coef: 2 },
          { code: "EC2", nom: "Docker & Kubernetes", note: 7.5, coef: 2 },
        ],
      },
      {
        code: "UE-INF102",
        nom: "Ingénierie des Données & Cloud",
        ects: 10,
        ecues: [
          { code: "EC3", nom: "Bases NoSQL & Graph", note: 7.0, coef: 1.5 },
          { code: "EC4", nom: "Cloud Computing AWS", note: 8.0, coef: 1.5 },
        ],
      },
      {
        code: "UE-MGT101",
        nom: "Management Agile & Anglais Tech",
        ects: 10,
        ecues: [
          { code: "EC5", nom: "Scrum & Kanban", note: 9.0, coef: 1 },
          { code: "EC6", nom: "Anglais Professionnel", note: 8.5, coef: 1 },
        ],
      },
    ],
  },
];
