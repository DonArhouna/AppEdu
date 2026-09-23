export type NiveauRelance = "NIVEAU_1" | "NIVEAU_2" | "NIVEAU_3";
export type CanalRelance = "EMAIL" | "SMS" | "COURRIER" | "TOUS";

export interface Debiteur {
  id: string;
  matricule: string;
  nom: string;
  prenom: string;
  email: string;
  telephone: string;
  filiere: string;
  numeroFacture: string;
  montantTotal: number;
  montantPaye: number;
  montantRestant: number;
  dateEmission: string;
  dateEcheance: string;
  joursRetard: number;
  trancheRetard: "NON_ECHU" | "1_30" | "31_60" | "61_90" | "PLUS_90";
  niveauRecommande: NiveauRelance;
  derniereRelance?: {
    date: string;
    niveau: NiveauRelance;
    canal: CanalRelance;
  };
}

export interface HistoriqueRelance {
  id: string;
  debiteurId: string;
  matricule: string;
  nomComplet: string;
  dateEnvoi: string;
  niveau: NiveauRelance;
  canal: CanalRelance;
  montantRappele: number;
  objet: string;
  contenu: string;
  statut: "ENVOYÉ" | "DISTRIBUÉ" | "LU";
}

export interface ModeleRelance {
  niveau: NiveauRelance;
  titre: string;
  delaiJoursMin: number;
  delaiJoursMax: number;
  ton: "Courtois" | "Ferme" | "Juridique / Contentieux";
  emailObjet: string;
  emailCorps: string;
  smsCorps: string;
  courrierCorps: string;
}

export const MODELES_RELANCE: Record<NiveauRelance, ModeleRelance> = {
  NIVEAU_1: {
    niveau: "NIVEAU_1",
    titre: "Niveau 1 — Rappel Amiable / Courtois",
    delaiJoursMin: 1,
    delaiJoursMax: 30,
    ton: "Courtois",
    emailObjet: "Rappel amical : Échéance de règlement pour {{prenom}} {{nom}} (Facture {{numero_facture}})",
    emailCorps: `Bonjour {{prenom}} {{nom}},\n\nSauf erreur ou omission de notre part, nous constatons que la facture n°{{numero_facture}} d'un montant de {{montant_du}} FCFA, venue à échéance le {{date_echeance}} (soit un retard de {{jours_retard}} jours), n'a pas encore été soldée.\n\nNous vous remercions de bien vouloir procéder à son règlement dans les meilleurs délais soit par virement bancaire sur notre compte {{iban}} (Banque : {{banque}}), soit à la caisse de l'établissement.\n\nSi votre versement a déjà été effectué entre-temps, nous vous prions de ne pas tenir compte de ce message.\n\nCordialement,\nLe Service Comptabilité & Recouvrement`,
    smsCorps: `AppEdu : Bonjour {{prenom}}, la facture n°{{numero_facture}} de {{montant_du}} FCFA est en attente de solde (échéance {{date_echeance}}). Merci de régulariser. Infos: comptabilite@universite.edu`,
    courrierCorps: `Madame, Monsieur,\n\nNos écritures font apparaître à ce jour un solde débiteur de {{montant_du}} FCFA au titre des frais de scolarité pour l'étudiant(e) {{prenom}} {{nom}} (Matricule {{matricule}}).\n\nNous vous prions de bien vouloir régulariser cette situation au plus tard sous huitaine.`,
  },
  NIVEAU_2: {
    niveau: "NIVEAU_2",
    titre: "Niveau 2 — Deuxième Rappel / Avertissement Ferme",
    delaiJoursMin: 31,
    delaiJoursMax: 60,
    ton: "Ferme",
    emailObjet: "URGENT : Deuxième avis d'impayé de scolarité - Dossier {{matricule}}",
    emailCorps: `Madame, Monsieur {{nom}},\n\nMalgré notre précédent rappel, nous n'avons toujours pas constaté le règlement de la facture n°{{numero_facture}} échue depuis {{jours_retard}} jours.\n\nLe montant restant dû s'élève à {{montant_du}} FCFA.\n\nNous vous prions d'effectuer le versement sous 5 jours ouvrés afin d'éviter tout désagrément administratif ou suspension temporaire des accès pédagogiques.\n\nCoordonnées bancaires :\nBanque : {{banque}}\nIBAN/RIB : {{iban}}\n\nComptabilité Universitaire`,
    smsCorps: `URGENT AppEdu: 2ème avis impayé pour {{prenom}} {{nom}}. Solde dû: {{montant_du}} FCFA (retard {{jours_retard}}j). Régularisation exigée sous 5 jours.`,
    courrierCorps: `Madame, Monsieur,\n\nMalgré notre première relance, nous constatons avec regret que votre compte reste débiteur de {{montant_du}} FCFA concernant les frais de scolarité de {{prenom}} {{nom}}.\n\nNous vous mettons en demeure de régulariser cette créance sous 5 jours à réception de ce courrier, sous peine de restriction des services pédagogiques.`,
  },
  NIVEAU_3: {
    niveau: "NIVEAU_3",
    titre: "Niveau 3 — Mise en Demeure Formelle & Contentieux",
    delaiJoursMin: 61,
    delaiJoursMax: 999,
    ton: "Juridique / Contentieux",
    emailObjet: "MISE EN DEMEURE FORMELLE AVANT PROCÉDURE CONTENTIEUSE - Réf: {{numero_facture}}",
    emailCorps: `LETTRE RECOMMANDÉE PAR VOIE ÉLECTRONIQUE\n\nMadame, Monsieur {{nom}},\n\nPar la présente, nous vous mettons formellement EN DEMEURE de nous régler la somme principale de {{montant_du}} FCFA correspondant aux frais de scolarité impayés (Facture {{numero_facture}} en retard de {{jours_retard}} jours).\n\nÀ défaut de paiement intégral sous 48 heures :\n1. L'accès aux plateformes de cours et aux salles d'examens sera suspendu ;\n2. Aucun relevé de notes ni diplôme ne pourra être délivré ;\n3. Le dossier sera transmis à notre cabinet de recouvrement / contentieux avec application de pénalités de retard légales.\n\nPour la Direction Administrative & Financière`,
    smsCorps: `ALERTE CONTENTIEUX AppEdu: Mise en demeure de payer {{montant_du}} FCFA sous 48h (Dossier {{matricule}}). Risque de blocage examens et diplômes.`,
    courrierCorps: `MISE EN DEMEURE DE PAYER\n\nMadame, Monsieur,\n\nVous restez redevable de la somme de {{montant_du}} FCFA au titre de la scolarité de {{prenom}} {{nom}} (Matricule {{matricule}}), impayée depuis {{jours_retard}} jours.\n\nFaute d'un règlement intégral sous 48 heures à compter de la réception de la présente, nous engagerons immédiatement les voies de recouvrement forcé et la suspension conservatoire de l'inscription académique.`,
  },
};

// Données initiales des débiteurs
export const INITIAL_DEBITEURS: Debiteur[] = [
  {
    id: "deb-1",
    matricule: "ETU-2024-002",
    nom: "Yao",
    prenom: "Adjoua",
    email: "adjoua.yao@universite.edu",
    telephone: "+225 07 45 12 89",
    filiere: "Master 1 Génie Logiciel",
    numeroFacture: "FAC-2024-002",
    montantTotal: 375000,
    montantPaye: 200000,
    montantRestant: 175000,
    dateEmission: "2024-01-15",
    dateEcheance: "2024-02-15",
    joursRetard: 22,
    trancheRetard: "1_30",
    niveauRecommande: "NIVEAU_1",
  },
  {
    id: "deb-2",
    matricule: "ETU-2024-003",
    nom: "Koné",
    prenom: "Mariam",
    email: "mariam.kone@universite.edu",
    telephone: "+225 05 11 22 33",
    filiere: "L2 Informatique & Réseaux",
    numeroFacture: "FAC-2024-003",
    montantTotal: 375000,
    montantPaye: 0,
    montantRestant: 375000,
    dateEmission: "2024-01-10",
    dateEcheance: "2024-02-10",
    joursRetard: 45,
    trancheRetard: "31_60",
    niveauRecommande: "NIVEAU_2",
    derniereRelance: {
      date: "2024-02-20",
      niveau: "NIVEAU_1",
      canal: "EMAIL",
    },
  },
  {
    id: "deb-3",
    matricule: "ETU-2024-007",
    nom: "Coulibaly",
    prenom: "Bakary",
    email: "bakary.c@universite.edu",
    telephone: "+225 01 88 99 77",
    filiere: "L3 Gestion de Projet",
    numeroFacture: "FAC-2023-088",
    montantTotal: 500000,
    montantPaye: 100000,
    montantRestant: 400000,
    dateEmission: "2023-11-15",
    dateEcheance: "2023-12-15",
    joursRetard: 110,
    trancheRetard: "PLUS_90",
    niveauRecommande: "NIVEAU_3",
    derniereRelance: {
      date: "2024-01-10",
      niveau: "NIVEAU_2",
      canal: "TOUS",
    },
  },
  {
    id: "deb-4",
    matricule: "ETU-2024-014",
    nom: "Traoré",
    prenom: "Fatimata",
    email: "fatimata.t@universite.edu",
    telephone: "+225 07 99 44 22",
    filiere: "Master 2 Finance & Audit",
    numeroFacture: "FAC-2024-005",
    montantTotal: 450000,
    montantPaye: 250000,
    montantRestant: 200000,
    dateEmission: "2024-01-05",
    dateEcheance: "2024-02-05",
    joursRetard: 72,
    trancheRetard: "61_90",
    niveauRecommande: "NIVEAU_3",
    derniereRelance: {
      date: "2024-02-12",
      niveau: "NIVEAU_2",
      canal: "SMS",
    },
  },
  {
    id: "deb-5",
    matricule: "ETU-2024-021",
    nom: "N'Guessan",
    prenom: "Serge",
    email: "serge.ng@universite.edu",
    telephone: "+225 05 33 22 11",
    filiere: "L1 Marketing Digital",
    numeroFacture: "FAC-2024-012",
    montantTotal: 300000,
    montantPaye: 150000,
    montantRestant: 150000,
    dateEmission: "2024-01-25",
    dateEcheance: "2024-02-25",
    joursRetard: 12,
    trancheRetard: "1_30",
    niveauRecommande: "NIVEAU_1",
  },
];

export const relanceService = {
  // Remplacer les variables du modèle
  interpolerMessage: (
    template: string,
    debiteur: Debiteur,
    banqueInfo = { nom: "Société Générale / Banque Atlantique", iban: "CI059 01001 002345678901 22" }
  ): string => {
    return template
      .replace(/{{prenom}}/g, debiteur.prenom)
      .replace(/{{nom}}/g, debiteur.nom)
      .replace(/{{matricule}}/g, debiteur.matricule)
      .replace(/{{numero_facture}}/g, debiteur.numeroFacture)
      .replace(/{{montant_du}}/g, debiteur.montantRestant.toLocaleString("fr-FR"))
      .replace(/{{date_echeance}}/g, debiteur.dateEcheance)
      .replace(/{{jours_retard}}/g, debiteur.joursRetard.toString())
      .replace(/{{banque}}/g, banqueInfo.nom)
      .replace(/{{iban}}/g, banqueInfo.iban);
  },

  // Calculer les statistiques de la balance âgée
  calculerStats: (debiteurs: Debiteur[]) => {
    const totalCreances = debiteurs.reduce((acc, d) => acc + d.montantRestant, 0);
    const tranche1_30 = debiteurs
      .filter((d) => d.trancheRetard === "1_30")
      .reduce((acc, d) => acc + d.montantRestant, 0);
    const tranche31_60 = debiteurs
      .filter((d) => d.trancheRetard === "31_60")
      .reduce((acc, d) => acc + d.montantRestant, 0);
    const tranche61_90 = debiteurs
      .filter((d) => d.trancheRetard === "61_90")
      .reduce((acc, d) => acc + d.montantRestant, 0);
    const tranchePlus90 = debiteurs
      .filter((d) => d.trancheRetard === "PLUS_90")
      .reduce((acc, d) => acc + d.montantRestant, 0);

    const totalCritique = tranche61_90 + tranchePlus90;
    const contentieuxCount = debiteurs.filter(
      (d) => d.trancheRetard === "61_90" || d.trancheRetard === "PLUS_90"
    ).length;

    return {
      totalCreances,
      tranche1_30,
      tranche31_60,
      tranche61_90,
      tranchePlus90,
      totalCritique,
      contentieuxCount,
      totalDebiteurs: debiteurs.length,
    };
  },

  // Envoyer une relance
  envoyerRelance: (
    debiteur: Debiteur,
    niveau: NiveauRelance,
    canal: CanalRelance,
    banqueInfo?: { nom: string; iban: string }
  ): HistoriqueRelance => {
    const modele = MODELES_RELANCE[niveau];
    const objet = relanceService.interpolerMessage(modele.emailObjet, debiteur, banqueInfo);
    const contenu =
      canal === "SMS"
        ? relanceService.interpolerMessage(modele.smsCorps, debiteur, banqueInfo)
        : relanceService.interpolerMessage(modele.emailCorps, debiteur, banqueInfo);

    return {
      id: `rel-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      debiteurId: debiteur.id,
      matricule: debiteur.matricule,
      nomComplet: `${debiteur.prenom} ${debiteur.nom}`,
      dateEnvoi: new Date().toISOString(),
      niveau,
      canal,
      montantRappele: debiteur.montantRestant,
      objet,
      contenu,
      statut: "ENVOYÉ",
    };
  },
};
