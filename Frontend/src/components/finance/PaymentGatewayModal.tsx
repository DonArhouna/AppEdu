import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  Smartphone,
  CreditCard,
  CheckCircle2,
  Loader2,
  ShieldCheck,
  Zap,
  ArrowRight
} from "lucide-react";
import { toast } from "sonner";

interface PaymentGatewayModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  montant: string;
  factureRef: string;
  etudiantNom: string;
  onSuccess?: () => void;
}

export const PaymentGatewayModal = ({
  open,
  onOpenChange,
  montant,
  factureRef,
  etudiantNom,
  onSuccess,
}: PaymentGatewayModalProps) => {
  const [method, setMethod] = useState<"wave" | "orange" | "moov" | "card">("wave");
  const [phone, setPhone] = useState("+225 07 00 11 22 33");
  const [cardNumber, setCardNumber] = useState("4532 •••• •••• 8910");
  const [step, setStep] = useState<"INIT" | "WAITING_WEBHOOK" | "SUCCESS">("INIT");

  const handleProcessPayment = (e: React.FormEvent) => {
    e.preventDefault();
    setStep("WAITING_WEBHOOK");
    toast.info("Validation du paiement envoyée à la passerelle Mobile Money / Banque...");

    // Simulate instant Webhook response from Wave / Orange Money / Visa Gateway
    setTimeout(() => {
      setStep("SUCCESS");
      toast.success(`Paiement de ${montant} validé via Webhook en temps réel !`);
      if (onSuccess) onSuccess();
    }, 2500);
  };

  const resetModal = () => {
    setStep("INIT");
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={resetModal}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg">
            <Zap className="h-5 w-5 text-amber-500" />
            Passerelle de Paiement Sécurisée
          </DialogTitle>
          <DialogDescription>
            Règlement en ligne des frais de scolarité pour {etudiantNom}
          </DialogDescription>
        </DialogHeader>

        {step === "INIT" && (
          <form onSubmit={handleProcessPayment} className="space-y-5 py-2">
            {/* Amount Banner */}
            <div className="p-4 rounded-xl bg-gradient-to-r from-primary/10 to-secondary/10 border border-primary/20 flex items-center justify-between">
              <div>
                <span className="text-xs text-muted-foreground block">Référence Facture :</span>
                <span className="font-mono font-bold text-sm text-foreground">{factureRef}</span>
              </div>
              <div className="text-right">
                <span className="text-xs text-muted-foreground block">Montant à régler :</span>
                <span className="text-xl font-extrabold text-primary">{montant}</span>
              </div>
            </div>

            {/* Method Selection */}
            <div className="space-y-2">
              <Label className="text-xs font-semibold">Méthode de Règlement</Label>
              <div className="grid grid-cols-4 gap-2">
                <button
                  type="button"
                  onClick={() => setMethod("wave")}
                  className={`p-2.5 rounded-xl border text-center transition-all ${
                    method === "wave"
                      ? "border-cyan-500 bg-cyan-500/10 font-bold text-cyan-700 ring-2 ring-cyan-500/30"
                      : "border-border hover:bg-muted"
                  }`}
                >
                  <span className="block text-xs font-bold">Wave</span>
                  <span className="text-[9px] text-muted-foreground">Mobile</span>
                </button>

                <button
                  type="button"
                  onClick={() => setMethod("orange")}
                  className={`p-2.5 rounded-xl border text-center transition-all ${
                    method === "orange"
                      ? "border-amber-500 bg-amber-500/10 font-bold text-amber-700 ring-2 ring-amber-500/30"
                      : "border-border hover:bg-muted"
                  }`}
                >
                  <span className="block text-xs font-bold">Orange</span>
                  <span className="text-[9px] text-muted-foreground">Money</span>
                </button>

                <button
                  type="button"
                  onClick={() => setMethod("moov")}
                  className={`p-2.5 rounded-xl border text-center transition-all ${
                    method === "moov"
                      ? "border-blue-500 bg-blue-500/10 font-bold text-blue-700 ring-2 ring-blue-500/30"
                      : "border-border hover:bg-muted"
                  }`}
                >
                  <span className="block text-xs font-bold">Moov</span>
                  <span className="text-[9px] text-muted-foreground">Money</span>
                </button>

                <button
                  type="button"
                  onClick={() => setMethod("card")}
                  className={`p-2.5 rounded-xl border text-center transition-all ${
                    method === "card"
                      ? "border-purple-500 bg-purple-500/10 font-bold text-purple-700 ring-2 ring-purple-500/30"
                      : "border-border hover:bg-muted"
                  }`}
                >
                  <span className="block text-xs font-bold">Carte</span>
                  <span className="text-[9px] text-muted-foreground">CB/Visa</span>
                </button>
              </div>
            </div>

            {/* Input Details */}
            {method !== "card" ? (
              <div className="space-y-2">
                <Label htmlFor="phone">Numéro du Compte Mobile Money</Label>
                <div className="relative">
                  <Smartphone className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="phone"
                    required
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="pl-9 text-sm"
                  />
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <Label htmlFor="card">Numéro de Carte Bancaire</Label>
                <div className="relative">
                  <CreditCard className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="card"
                    required
                    value={cardNumber}
                    onChange={(e) => setCardNumber(e.target.value)}
                    className="pl-9 text-sm font-mono"
                  />
                </div>
              </div>
            )}

            <Button type="submit" className="w-full shadow-lg">
              Payer {montant} Maintenant
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          </form>
        )}

        {step === "WAITING_WEBHOOK" && (
          <div className="py-12 text-center space-y-4">
            <div className="relative flex items-center justify-center mx-auto">
              <div className="h-16 w-16 rounded-full border-4 border-primary/20 border-t-primary animate-spin" />
              <Zap className="h-8 w-8 text-primary absolute animate-pulse" />
            </div>

            <div className="space-y-1">
              <h3 className="text-lg font-bold text-foreground">En attente de la notification Webhook...</h3>
              <p className="text-xs text-muted-foreground max-w-xs mx-auto">
                La passerelle traite le débit du compte. Dès confirmation, le système mettra à jour automatiquement le statut de la facture.
              </p>
            </div>

            <Badge variant="outline" className="animate-pulse font-mono text-[10px]">
              LISTEN_WEBHOOK_EVENT: payment.succeeded
            </Badge>
          </div>
        )}

        {step === "SUCCESS" && (
          <div className="py-8 text-center space-y-5">
            <div className="h-16 w-16 rounded-full bg-emerald-500/20 text-emerald-600 flex items-center justify-center mx-auto animate-bounce">
              <CheckCircle2 className="h-10 w-10" />
            </div>

            <div className="space-y-1">
              <h3 className="text-xl font-bold text-foreground">Paiement Confirmé !</h3>
              <p className="text-xs text-muted-foreground">
                Reçu généré et envoyé instantanément par email et SMS.
              </p>
            </div>

            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-200 text-xs font-mono text-emerald-900">
              Transaction #TXN-2026-99081 • Statut: PAYÉ
            </div>

            <Button onClick={resetModal} className="w-full">
              Fermer et Voir le Reçu
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
