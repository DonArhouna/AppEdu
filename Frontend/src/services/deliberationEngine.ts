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
  seuilEliminatoire: number; // Seuil 7.0 : une note inférieure déclenche un rattrapage
  seuilPassageConditionnelECTS: number; // Default 18 ECTS out of 30
  compensationAutorisee: boolean; // Default true (inter-UE compensation if sem average >= 10)
}

export const DEFAULT_DELIBERATION_CONFIG: DeliberationConfig = {
  seuilValidationMoyenne: 10.0,
  seuilEliminatoire: 7.0,
  seuilPassageConditionnelECTS: 18,
  compensationAutorisee: true,
};

export interface DeliberationStudentInput {
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
}

export const deliberationEngine = {
  // Calculer la délibération individuelle pour un étudiant
  calculerEtudiant: (
    etudiantRaw: DeliberationStudentInput,
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
    etudiants: DeliberationStudentInput[],
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
