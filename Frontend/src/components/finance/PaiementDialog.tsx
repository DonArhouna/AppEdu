/**
 * Composant PaiementDialog
 * Fenêtre de dialogue modale pour l'enregistrement des règlements avec calcul dynamique
 * des périodes selon la session académique rattachée à l'étudiant.
 */

import { PaiementPhysiqueModal, PaiementPhysiqueModalProps } from "./PaiementPhysiqueModal";

export const PaiementDialog = (props: PaiementPhysiqueModalProps) => {
  return <PaiementPhysiqueModal {...props} />;
};

export default PaiementDialog;
