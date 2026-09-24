import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Printer, CheckCircle2, Calendar, FileText, QrCode } from "lucide-react";

export interface ReceiptData {
  numRecu: string;
  datePaiement: string;
  etudiant: {
    matricule: string;
    nom: string;
    prenom: string;
    filiere: string;
    niveau: string;
  };
  modePaiement: string; // Espèces, Chèque, POS, Mobile Money
  referencePaiement?: string;
  periodesPayees: string[];
  montantDetail: {
    droitsInscription?: number;
    scolariteMensuelle?: number;
    total: number;
    paye: number;
    reste: number;
  };
  caissier?: string;
  devise?: string;
  sessionId?: string;
  sessionNom?: string;
  etablissement?: {
    nom?: string;
    code?: string;
    devise?: string;
  };
}

interface ReceiptModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  receiptData: ReceiptData | null;
}

export const ReceiptModal = ({ open, onOpenChange, receiptData }: ReceiptModalProps) => {
  if (!receiptData) return null;

  const handlePrint = () => {
    window.print();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[650px] max-h-[90vh] overflow-y-auto p-0">
        <div id="printable-receipt" className="p-6 sm:p-8 space-y-6 bg-background text-foreground">
          {/* Header Receipt */}
          <div className="flex items-start justify-between border-b pb-4">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary font-bold text-lg">
                {receiptData.etablissement?.code || "ÉTABLISSEMENT"}
              </div>
              <div>
                <h3 className="font-bold text-lg text-foreground">{receiptData.etablissement?.nom || "Établissement"}</h3>
                <p className="text-xs text-muted-foreground">Code établissement : {receiptData.etablissement?.code || "-"}</p>
              </div>
            </div>
            <div className="text-right">
              <Badge variant="outline" className="text-xs font-mono font-bold bg-primary/5 text-primary border-primary/30">
                REÇU N° {receiptData.numRecu}
              </Badge>
              <p className="text-xs text-muted-foreground mt-1 flex items-center justify-end gap-1">
                <Calendar className="h-3 w-3" /> Date: {receiptData.datePaiement}
              </p>
            </div>
          </div>

          {/* Student Info Box */}
          <div className="rounded-xl border bg-muted/30 p-4 grid grid-cols-2 gap-4 text-xs">
            <div>
              <span className="text-muted-foreground uppercase font-semibold text-[10px]">Étudiant :</span>
              <p className="font-bold text-sm text-foreground mt-0.5">
                {receiptData.etudiant.prenom} {receiptData.etudiant.nom}
              </p>
              <p className="text-muted-foreground font-mono text-[11px] mt-0.5">
                Matricule: <span className="font-semibold text-foreground">{receiptData.etudiant.matricule}</span>
              </p>
            </div>
            <div>
              <span className="text-muted-foreground uppercase font-semibold text-[10px]">Inscription Académique :</span>
              <p className="font-semibold text-foreground mt-0.5">{receiptData.etudiant.filiere}</p>
              <p className="text-muted-foreground text-[11px] mt-0.5">Niveau: <span className="font-semibold text-foreground">{receiptData.etudiant.niveau}</span></p>
            </div>
          </div>

          {/* Payment Breakdown Table */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <FileText className="h-3.5 w-3.5 text-primary" /> Détail du Règlement
            </h4>
            <div className="border rounded-xl overflow-hidden text-xs">
              <div className="grid grid-cols-3 bg-muted/60 p-2.5 font-semibold text-muted-foreground border-b">
                <span>Désignation / Périodes</span>
                <span className="text-center">Mode</span>
                <span className="text-right">Montant</span>
              </div>
              <div className="p-3 space-y-2">
                <div className="flex justify-between items-center">
                  <div>
                    <p className="font-semibold text-foreground">
                      Paiement Scolarité : {receiptData.periodesPayees.join(", ")}
                    </p>
                    <p className="text-[11px] text-muted-foreground">
                      Réf: {receiptData.referencePaiement || "Référence non renseignée"}
                    </p>
                  </div>
                  <Badge variant="secondary" className="font-mono text-[11px]">
                    {receiptData.modePaiement}
                  </Badge>
                  <span className="font-mono font-bold text-foreground">
                    {receiptData.montantDetail.paye.toLocaleString()} {receiptData.devise || receiptData.etablissement?.devise || ""}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Totals Summary */}
          <div className="bg-primary/5 rounded-xl p-4 border border-primary/20 space-y-2 text-xs">
            <div className="flex justify-between text-muted-foreground">
              <span>Montant Total Configurépour la Période :</span>
              <span className="font-mono font-semibold">{receiptData.montantDetail.total.toLocaleString()} {receiptData.devise || receiptData.etablissement?.devise || ""}</span>
            </div>
            <div className="flex justify-between text-emerald-600 font-bold text-sm pt-1 border-t border-primary/10">
              <span>Montant Encaissé (Ce jour) :</span>
              <span className="font-mono">{receiptData.montantDetail.paye.toLocaleString()} {receiptData.devise || receiptData.etablissement?.devise || ""}</span>
            </div>
            {receiptData.montantDetail.reste > 0 ? (
              <div className="flex justify-between text-amber-600 font-semibold pt-1">
                <span>Reste à Payer (Solde) :</span>
                <span className="font-mono">{receiptData.montantDetail.reste.toLocaleString()} {receiptData.devise || receiptData.etablissement?.devise || ""}</span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-emerald-600 font-semibold text-[11px] pt-1">
                <CheckCircle2 className="h-3.5 w-3.5" /> Règlement enregistré par l'API
              </div>
            )}
          </div>

          {/* Stamp & Verification */}
          <div className="flex items-end justify-between pt-4 border-t border-dashed">
            <div className="flex items-center gap-2">
              <QrCode className="h-12 w-12 text-muted-foreground/60" />
              <div className="text-[10px] text-muted-foreground">
                <p className="font-semibold text-foreground">Reçu généré par le serveur</p>
                <p>Référence interne : {receiptData.numRecu}</p>
                {receiptData.caissier && <p>Encaissé par : {receiptData.caissier}</p>}
              </div>
            </div>
            <div className="text-center">
              <div className="h-12 w-28 border border-dashed border-muted-foreground/40 rounded-lg flex items-center justify-center text-[10px] text-muted-foreground font-mono">
                [ Cachet Caisse ]
              </div>
            </div>
          </div>
        </div>

        {/* Modal Actions */}
        <div className="p-4 bg-muted/30 border-t flex justify-end gap-3">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Fermer
          </Button>
          <Button onClick={handlePrint} className="gap-2">
            <Printer className="h-4 w-4" /> Imprimer le Reçu
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
