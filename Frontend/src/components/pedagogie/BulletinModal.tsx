import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Download, Printer, ShieldCheck, QrCode, FileText } from "lucide-react";
import logo from "@/assets/logo.svg";

interface BulletinModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  studentName?: string;
  matricule?: string;
}

export const BulletinModal = ({
  open,
  onOpenChange,
  studentName = "Marie Dupont",
  matricule = "ETU-2026-0042",
}: BulletinModalProps) => {
  const notesData = [
    { ue: "UE1: Algorithmique & Développement", matiere: "Algorithmique Avancée", coef: 4, note: 16.5, statut: "Validé" },
    { ue: "UE1: Algorithmique & Développement", matiere: "Programmation Web React", coef: 3, note: 17.0, statut: "Validé" },
    { ue: "UE2: Bases de Données & Systèmes", matiere: "PostgreSQL & Modélisation SQL", coef: 3, note: 14.5, statut: "Validé" },
    { ue: "UE2: Bases de Données & Systèmes", matiere: "Architecture Réseaux & Cloud", coef: 2, note: 13.0, statut: "Validé" },
    { ue: "UE3: Management & Langues", matiere: "Anglais Technique", coef: 2, note: 15.0, statut: "Validé" },
    { ue: "UE3: Management & Langues", matiere: "Gestion de Projet Agile", coef: 2, note: 16.0, statut: "Validé" },
  ];

  const totalCoef = notesData.reduce((acc, n) => acc + n.coef, 0);
  const totalNotePonderee = notesData.reduce((acc, n) => acc + n.note * n.coef, 0);
  const moyenneGenerale = (totalNotePonderee / totalCoef).toFixed(2);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[750px] max-h-[90vh] overflow-y-auto">
        <DialogHeader className="flex flex-row items-center justify-between border-b pb-4">
          <DialogTitle className="flex items-center gap-2 text-lg">
            <FileText className="h-5 w-5 text-primary" />
            Bulletin Officiel de Notes - Semestre 1
          </DialogTitle>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={() => window.print()}>
              <Printer className="h-4 w-4 mr-1" /> Imprimer / PDF
            </Button>
          </div>
        </DialogHeader>

        {/* Printable Bulletin Document */}
        <div className="space-y-6 py-4 bg-white text-black p-6 rounded-xl border shadow-inner">
          {/* Header Institution */}
          <div className="flex justify-between items-start border-b pb-4">
            <div className="flex items-center gap-3">
              <img src={logo} alt="EduManagePro" className="h-12 w-12 object-contain" />
              <div>
                <h2 className="font-bold text-base text-slate-900 uppercase tracking-tight">
                  Institut Supérieur EduManagePro
                </h2>
                <p className="text-xs text-slate-600">
                  Décret d'Habilitation N° 2024/MIN-EDUC/099
                </p>
                <p className="text-[11px] text-slate-500">Campus Central • Année Académique 2025-2026</p>
              </div>
            </div>

            <div className="text-right">
              <Badge className="bg-emerald-600 text-white font-mono text-xs">
                OFFICIEL • S1
              </Badge>
              <p className="text-[10px] text-slate-500 mt-1 font-mono">Doc ID: BUL-2026-8849</p>
            </div>
          </div>

          {/* Student Banner */}
          <div className="grid grid-cols-2 gap-4 bg-slate-50 p-3 rounded-lg border text-xs">
            <div>
              <span className="text-slate-500 block">Étudiant(e) :</span>
              <strong className="text-slate-900 text-sm">{studentName}</strong>
              <span className="text-slate-600 block">Matricule: {matricule}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Filière / Niveau :</span>
              <strong className="text-slate-900 text-sm">Master 1 Génie Logiciel</strong>
              <span className="text-slate-600 block">Système LMD (30 Crédits ECTS)</span>
            </div>
          </div>

          {/* Notes Table */}
          <Table className="border text-xs">
            <TableHeader className="bg-slate-100">
              <TableRow>
                <TableHead className="font-bold text-slate-800">Unités d'Enseignement & ECUE</TableHead>
                <TableHead className="text-center font-bold text-slate-800">Coef.</TableHead>
                <TableHead className="text-center font-bold text-slate-800">Note / 20</TableHead>
                <TableHead className="text-center font-bold text-slate-800">Statut</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {notesData.map((row, i) => (
                <TableRow key={i}>
                  <TableCell className="font-medium text-slate-900">
                    <span className="text-[10px] text-slate-500 block">{row.ue}</span>
                    {row.matiere}
                  </TableCell>
                  <TableCell className="text-center font-semibold">{row.coef}</TableCell>
                  <TableCell className="text-center font-mono font-bold text-slate-900">
                    {row.note.toFixed(1)}
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 text-[10px]">
                      {row.statut}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {/* Summary Banner */}
          <div className="p-4 rounded-xl bg-slate-900 text-white flex justify-between items-center">
            <div>
              <span className="text-xs text-slate-400 block">Moyenne Générale Pondérée :</span>
              <span className="text-2xl font-extrabold text-amber-400">{moyenneGenerale} / 20</span>
            </div>
            <div className="text-right">
              <span className="text-xs text-slate-400 block">Décision du Jury :</span>
              <span className="text-sm font-bold text-emerald-400">ADMIS(E) - MENTION BIEN</span>
            </div>
          </div>

          {/* Verification Footer with Signatures & QR Code */}
          <div className="pt-4 border-t flex justify-between items-center text-xs">
            <div className="flex items-center gap-3">
              <div className="h-14 w-14 bg-slate-100 border rounded flex items-center justify-center">
                <QrCode className="h-10 w-10 text-slate-800" />
              </div>
              <div className="text-[10px] text-slate-500">
                <span className="font-semibold text-slate-700 block">Vérification d'Authenticité :</span>
                Scannez pour vérifier la validité de ce bulletin sur edu.manage/verify
              </div>
            </div>

            <div className="text-center font-serif text-slate-700">
              <p className="text-[10px] text-slate-500">Fait à Paris, le 28 Août 2026</p>
              <p className="font-bold text-xs mt-1">Le Directeur Académique</p>
              <div className="h-8 italic text-slate-400 flex items-center justify-center text-xs">
                [ Cachet & Signature Numérique ]
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
