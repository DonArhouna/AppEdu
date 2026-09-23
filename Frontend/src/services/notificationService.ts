export type NotificationChannel = "SMS" | "EMAIL" | "BOTH";

export interface NotificationTemplate {
  statut: string;
  titre: string;
  emailSubject: string;
  emailBody: string;
  smsBody: string;
}

export interface NotificationLog {
  id: string;
  candidatId: string;
  candidatNom: string;
  candidatEmail: string;
  candidatTelephone: string;
  statut: string;
  channel: NotificationChannel;
  messagePreview: string;
  timestamp: string;
  statutEnvoi: "DELIVERED" | "SENT" | "PENDING";
}

const DEFAULT_TEMPLATES: Record<string, NotificationTemplate> = {
  recue: {
    statut: "recue",
    titre: "Candidature Reçue",
    emailSubject: "Confirmation de réception de votre dossier de candidature — {{etablissement}}",
    emailBody: "Bonjour {{prenom}},\n\nNous vous confirmons la bonne réception de votre dossier de candidature pour la filière {{filiere}}.\nNotre commission pédagogique procède actuellement à son instruction.\n\nCordialement,\nLe Service des Admissions — {{etablissement}}",
    smsBody: "{{etablissement}} : Bonjour {{prenom}}, votre candidature en {{filiere}} a bien été reçue. Vous serez notifié des prochaines étapes.",
  },
  examen: {
    statut: "examen",
    titre: "Dossier en Examen Pédagogique",
    emailSubject: "Votre dossier est en cours d'examen — {{etablissement}}",
    emailBody: "Bonjour {{prenom}},\n\nVotre dossier de candidature pour la formation {{filiere}} est actuellement en cours d'évaluation par la commission pédagogique.\nUne décision vous sera communiquée dans les plus brefs délais.\n\nCordialement,\nLa Commission Pédagogique — {{etablissement}}",
    smsBody: "{{etablissement}} : Bonjour {{prenom}}, votre dossier en {{filiere}} est en cours d'examen par la commission pédagogique.",
  },
  pieces_manquantes: {
    statut: "pieces_manquantes",
    titre: "Pièces Justificatives Manquantes",
    emailSubject: "Action requise : Pièces manquantes pour votre dossier — {{etablissement}}",
    emailBody: "Bonjour {{prenom}},\n\nAprès vérification de votre candidature pour la filière {{filiere}}, des pièces justificatives obligatoires sont manquantes ou non conformes :\n\n⚠️ Pièces à fournir : {{pieces_manquantes}}\n\nMerci de vous connecter à votre espace candidat pour téléverser ces documents sous 72 heures afin que votre dossier puisse être validé.\n\nCordialement,\nLe Bureau des Inscriptions — {{etablissement}}",
    smsBody: "{{etablissement}} : URGENT {{prenom}}, des pièces manquent à votre dossier en {{filiere}} ({{pieces_manquantes}}). Merci de les fournir sous 72h.",
  },
  admis: {
    statut: "admis",
    titre: "Félicitations, Candidature Acceptée",
    emailSubject: "Félicitations ! Vous êtes admis en {{filiere}} — {{etablissement}}",
    emailBody: "Cher(e) {{prenom}} {{nom}},\n\nNous avons le plaisir de vous informer que la commission pédagogique a validé votre admission en {{filiere}} pour l'année académique {{annee}}.\n\nPour finaliser votre inscription administrative et réserver votre place, veuillez procéder au règlement de vos frais d'inscription ou du premier acompte.\n\nBienvenue parmi nous !\nLa Direction — {{etablissement}}",
    smsBody: "FELICITATIONS {{prenom}} ! Vous êtes admis en {{filiere}} à {{etablissement}}. Finalisez votre inscription sur votre portail.",
  },
  inscrit: {
    statut: "inscrit",
    titre: "Inscription Définitive Confirmée",
    emailSubject: "Confirmation d'inscription définitive & Carte d'étudiant — {{etablissement}}",
    emailBody: "Bonjour {{prenom}},\n\nVotre inscription définitive en {{filiere}} est désormais validée. Votre matricule étudiant et votre certificat de scolarité sont disponibles en téléchargement sur votre Espace Étudiant.\n\nBonne rentrée académique !\nLe Secrétariat Général — {{etablissement}}",
    smsBody: "{{etablissement}} : {{prenom}}, votre inscription définitive en {{filiere}} est validée. Consultez votre Espace Étudiant.",
  },
};

const TEMPLATE_STORAGE_KEY = "edumanage_admission_templates";
const LOG_STORAGE_KEY = "edumanage_notification_logs";

export const notificationService = {
  // Récupérer les templates (avec persistance locale)
  getTemplates: (): Record<string, NotificationTemplate> => {
    if (typeof window === "undefined") return DEFAULT_TEMPLATES;
    const stored = localStorage.getItem(TEMPLATE_STORAGE_KEY);
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch (e) {
        return DEFAULT_TEMPLATES;
      }
    }
    return DEFAULT_TEMPLATES;
  },

  // Sauvegarder les templates modifiés
  saveTemplates: (templates: Record<string, NotificationTemplate>) => {
    if (typeof window !== "undefined") {
      localStorage.setItem(TEMPLATE_STORAGE_KEY, JSON.stringify(templates));
    }
  },

  // Résoudre les variables dynamiques
  renderTemplate: (
    templateString: string,
    variables: {
      prenom: string;
      nom: string;
      filiere: string;
      pieces_manquantes?: string;
      etablissement?: string;
      annee?: string;
    }
  ): string => {
    let result = templateString;
    result = result.replace(/{{prenom}}/g, variables.prenom || "");
    result = result.replace(/{{nom}}/g, variables.nom || "");
    result = result.replace(/{{filiere}}/g, variables.filiere || "");
    result = result.replace(
      /{{pieces_manquantes}}/g,
      variables.pieces_manquantes || "Relevé de notes officiel, Pièce d'identité"
    );
    result = result.replace(/{{etablissement}}/g, variables.etablissement || "Institut Supérieur EduManagePro");
    result = result.replace(/{{annee}}/g, variables.annee || "2025-2026");
    return result;
  },

  // Déclencher une notification automatique
  sendNotification: (
    candidat: {
      id: string;
      nom: string;
      prenom: string;
      email: string;
      telephone: string;
      filiere: string;
      piecesManquantes?: string[];
    },
    statutCible: string
  ): { emailSent: string; smsSent: string } => {
    const templates = notificationService.getTemplates();
    const template = templates[statutCible] || DEFAULT_TEMPLATES[statutCible] || DEFAULT_TEMPLATES.recue;

    const variables = {
      prenom: candidat.prenom,
      nom: candidat.nom,
      filiere: candidat.filiere,
      pieces_manquantes: candidat.piecesManquantes && candidat.piecesManquantes.length > 0
        ? candidat.piecesManquantes.join(", ")
        : "Relevé de notes certifié, Photocopie CNI/Passeport",
      etablissement: "Institut Supérieur EduManagePro",
      annee: "2025-2026",
    };

    const emailBody = notificationService.renderTemplate(template.emailBody, variables);
    const smsBody = notificationService.renderTemplate(template.smsBody, variables);

    // Enregistrer dans l'historique
    const newLog: NotificationLog = {
      id: `NOTIF-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
      candidatId: candidat.id,
      candidatNom: `${candidat.prenom} ${candidat.nom}`,
      candidatEmail: candidat.email,
      candidatTelephone: candidat.telephone,
      statut: statutCible,
      channel: "BOTH",
      messagePreview: smsBody,
      timestamp: new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }),
      statutEnvoi: "DELIVERED",
    };

    const logs = notificationService.getLogs();
    const updatedLogs = [newLog, ...logs];
    if (typeof window !== "undefined") {
      localStorage.setItem(LOG_STORAGE_KEY, JSON.stringify(updatedLogs));
    }

    return { emailSent: emailBody, smsSent: smsBody };
  },

  // Récupérer l'historique des notifications
  getLogs: (): NotificationLog[] => {
    if (typeof window === "undefined") return [];
    const stored = localStorage.getItem(LOG_STORAGE_KEY);
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch (e) {
        return [];
      }
    }
    return [];
  },

  // Récupérer les notifications pour un candidat donné
  getLogsForCandidat: (candidatId: string): NotificationLog[] => {
    return notificationService.getLogs().filter((log) => log.candidatId === candidatId);
  },
};
