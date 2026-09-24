import { AlertTriangle, CreditCard, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface PaymentGatewayModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  montant: string;
  factureRef: string;
  etudiantNom: string;
  onSuccess?: () => void;
}

/**
 * La passerelle en ligne n'est pas activée tant qu'aucun prestataire
 * de paiement n'est configuré côté serveur. Cette fenêtre ne simule
 * donc jamais un débit ni un reçu.
 */
export const PaymentGatewayModal = ({
  open,
  onOpenChange,
  montant,
  factureRef,
  etudiantNom,
}: PaymentGatewayModalProps) => (
  <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="sm:max-w-[480px]">
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2 text-lg">
          <CreditCard className="h-5 w-5 text-muted-foreground" />
          Paiement en ligne indisponible
        </DialogTitle>
        <DialogDescription>
          Aucun prestataire de paiement n'est configuré pour cette instance.
        </DialogDescription>
      </DialogHeader>
      <div className="space-y-4 py-2">
        <div className="flex gap-3 rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-sm text-amber-800 dark:text-amber-200">
          <AlertTriangle className="h-5 w-5 shrink-0" />
          <p>
            Aucun débit ne sera effectué. Utilisez le guichet pour enregistrer un règlement réellement validé par l'API.
          </p>
        </div>
        <div className="rounded-xl border bg-muted/30 p-4 text-sm">
          <div className="flex justify-between gap-4"><span className="text-muted-foreground">Étudiant</span><span className="font-medium">{etudiantNom}</span></div>
          <div className="mt-2 flex justify-between gap-4"><span className="text-muted-foreground">Facture</span><span className="font-mono">{factureRef}</span></div>
          <div className="mt-2 flex justify-between gap-4"><span className="text-muted-foreground">Montant</span><span className="font-semibold">{montant}</span></div>
        </div>
        <Button className="w-full" onClick={() => onOpenChange(false)}>
          <X className="mr-2 h-4 w-4" /> Fermer
        </Button>
      </div>
    </DialogContent>
  </Dialog>
);

export default PaymentGatewayModal;
