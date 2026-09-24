import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Printer, QrCode, CreditCard, Sparkles } from "lucide-react";
import logo from "@/assets/logo.svg";

interface StudentCardModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  student?: {
    nom: string;
    prenom: string;
    matricule: string;
    filiere: string;
    niveau: string;
    telephone: string;
    email: string;
  };
  sessionLabel?: string;
  status?: string;
  validUntil?: string;
}

export const StudentCardModal = ({
  open,
  onOpenChange,
  student,
  sessionLabel,
  status,
  validUntil,
}: StudentCardModalProps) => {
  if (!student) return null;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader className="flex flex-row items-center justify-between border-b pb-3">
          <DialogTitle className="flex items-center gap-2 text-base">
            <CreditCard className="h-5 w-5 text-primary" />
            Carte d'Étudiant Officielle (Badge Numérique)
          </DialogTitle>
          <Button size="sm" variant="outline" onClick={() => window.print()}>
            <Printer className="h-3.5 w-3.5 mr-1" /> Imprimer Badge
          </Button>
        </DialogHeader>

        {/* Printable Student ID Card (Format ISO Badge) */}
        <div className="py-4 flex justify-center">
          <div className="w-[360px] h-[220px] rounded-2xl bg-gradient-to-br from-sidebar via-sidebar/90 to-primary p-4 text-white shadow-2xl relative overflow-hidden border border-white/20 flex flex-col justify-between">
            {/* Background Graphic */}
            <div className="absolute right-0 top-0 bottom-0 opacity-10 pointer-events-none">
              <Sparkles className="h-48 w-48 -mr-10 -mt-10" />
            </div>

            {/* Top Brand */}
            <div className="flex items-center justify-between border-b border-white/20 pb-2 relative z-10">
              <div className="flex items-center gap-2">
                <img src={logo} alt="EduManagePro" className="h-6 w-6 object-contain" />
                <span className="font-bold text-xs tracking-tight">EduManagePro</span>
              </div>
              <Badge className="bg-white/20 text-white border-none text-[9px]">
                {sessionLabel || "Session non renseignée"}
              </Badge>
            </div>

            {/* Middle Info */}
            <div className="flex items-center gap-3 relative z-10 my-1">
              <div className="h-16 w-16 rounded-xl bg-white/20 border border-white/40 flex items-center justify-center font-bold text-lg text-white shrink-0 shadow-inner">
                {student.prenom[0]}
                {student.nom[0]}
              </div>

              <div className="min-w-0 flex-1 space-y-0.5">
                <h3 className="font-extrabold text-sm leading-tight truncate">
                  {student.prenom} {student.nom}
                </h3>
                <p className="text-[11px] text-white/80 font-medium truncate">
                  {student.filiere}
                </p>
                <p className="text-[10px] font-mono text-amber-300 font-bold">
                  Matricule: {student.matricule}
                </p>
              </div>
            </div>

            {/* Bottom Bar with QR Code & Barcode */}
            <div className="flex items-center justify-between border-t border-white/20 pt-2 relative z-10">
              <div className="font-mono text-[9px] text-white/70">
                <span>STATUT: {status || "NON RENSEIGNÉ"}</span>
                <span className="block text-[8px] text-white/50">VALIDITÉ : {validUntil || "NON RENSEIGNÉE"}</span>
              </div>
              <div className="h-8 w-8 bg-white p-0.5 rounded flex items-center justify-center">
                <QrCode className="h-full w-full text-black" />
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
