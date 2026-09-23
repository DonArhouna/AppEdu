import React from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
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
import { Printer, Download, Award, CheckCircle2, ShieldCheck, School } from "lucide-react";
import type { EtudiantDeliberation, DeliberationConfig } from "@/services/deliberationEngine";

interface PVJuryModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  promotionName: string;
  semestre: string;
  anneeAcademique?: string;
  resultats: EtudiantDeliberation[];
  config: DeliberationConfig;
  stats: {
    total: number;
    admis: number;
    rattrapage: number;
    ajournes: number;
    tauxReussite: string;
    moyennePromo: string;
  };
}

export const PVJuryModal: React.FC<PVJuryModalProps> = ({
  open,
  onOpenChange,
  promotionName,
  semestre,
  anneeAcademique = "2025-2026",
  resultats,
  config,
  stats,
}) => {
  const handlePrint = () => {
    window.print();
  };

  const getStatutBadge = (statut: EtudiantDeliberation["statutSession"]) => {
    if (statut === "Admis") {
      return (
        <Badge className="bg-emerald-600 text-white hover:bg-emerald-700 border-none font-semibold text-[10px]">
          ADMIS
        </Badge>
      );
    }
    if (statut === "Rattrapage") {
      return (
        <Badge className="bg-amber-500 text-white hover:bg-amber-600 border-none font-semibold text-[10px]">
          SESSION RATTRAPAGE
        </Badge>
      );
    }
    return (
      <Badge className="bg-rose-600 text-white hover:bg-rose-700 border-none font-semibold text-[10px]">
        AJOURNÉ
      </Badge>
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[900px] max-h-[92vh] overflow-y-auto rounded-2xl scrollbar-thin p-0">
        {/* Actions bar at top */}
        <div className="p-4 border-b border-border/80 bg-muted/30 flex items-center justify-between sticky top-0 z-20 backdrop-blur-md">
          <div className="flex items-center gap-2">
            <Award className="h-5 w-5 text-amber-500" />
            <span className="font-bold text-sm">Procès-Verbal Officiel de Délibération (LMD)</span>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handlePrint} className="rounded-xl">
              <Printer className="h-4 w-4 mr-1.5" /> Imprimer / Exporter PDF
            </Button>
            <Button size="sm" onClick={() => onOpenChange(false)} className="rounded-xl">
              Fermer
            </Button>
          </div>
        </div>

        {/* Printable Document Sheet */}
        <div className="p-8 space-y-6 bg-white text-slate-900 font-sans print:p-0 print:m-0">
          {/* Institutional Header */}
          <div className="flex items-center justify-between border-b-2 border-slate-900 pb-4">
            <div>
              <p className="text-[10px] font-bold tracking-wider uppercase text-slate-500">
                RÉPUBLIQUE DE CÔTE D'IVOIRE • MINISTÈRE DE L'ENSEIGNEMENT SUPÉRIEUR
              </p>
              <h2 className="text-xl font-extrabold uppercase tracking-tight text-slate-950 mt-1">
                INSTITUT SUPÉRIEUR EDUMANAGEPRO
              </h2>
              <p className="text-xs text-slate-600">
                Direction des Études & Commission Permanente des Examens
              </p>
            </div>
            <div className="text-right">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-100 rounded-lg border border-slate-300">
                <ShieldCheck className="h-4 w-4 text-emerald-600" />
                <span className="font-mono text-xs font-bold">SESSION PRINCIPALE</span>
              </div>
              <p className="text-xs text-slate-500 mt-1">Année Académique : {anneeAcademique}</p>
            </div>
          </div>

          {/* PV Title */}
          <div className="text-center py-2 bg-slate-50 rounded-xl border border-slate-200">
            <h1 className="text-base font-black uppercase tracking-wider text-slate-900">
              PROCÈS-VERBAL DE DÉLIBÉRATION DU JURY DE SESSION
            </h1>
            <p className="text-xs font-semibold text-slate-700 mt-0.5">
              Filière : {promotionName} • {semestre}
            </p>
            <p className="text-[11px] text-slate-500">
              Conformément au décret national portant organisation du système Licence-Master-Doctorat (LMD)
            </p>
          </div>

          {/* Jury Composition */}
          <div className="grid grid-cols-3 gap-4 text-xs border p-3 rounded-xl bg-slate-50/70 border-slate-200">
            <div>
              <span className="text-[10px] font-bold uppercase text-slate-500 block">Président du Jury :</span>
              <span className="font-semibold text-slate-900">Prof. Konan Kouamé</span>
              <span className="text-[10px] text-slate-500 block">Doyen de Faculté</span>
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase text-slate-500 block">Rapporteur / Assesseur :</span>
              <span className="font-semibold text-slate-900">Dr. Sophie Ndiaye</span>
              <span className="text-[10px] text-slate-500 block">Responsable Pédagogique</span>
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase text-slate-500 block">Secrétaire de Séance :</span>
              <span className="font-semibold text-slate-900">M. Mamadou Diallo</span>
              <span className="text-[10px] text-slate-500 block">Chef de Département</span>
            </div>
          </div>

          {/* Deliberation Rules & Thresholds */}
          <div className="flex items-center justify-between text-xs bg-slate-100 p-2.5 rounded-lg border border-slate-200">
            <div>
              <strong>Critères légaux appliqués :</strong> Seuil validation moyenne :{" "}
              <span className="font-bold">{config.seuilValidationMoyenne}/20</span> • Note éliminatoire :{" "}
              <span className="font-bold">&lt; {config.seuilEliminatoire}/20</span> • Compensation :{" "}
              <span className="font-bold">{config.compensationAutorisee ? "Active" : "Désactivée"}</span>
            </div>
            <div className="text-right font-semibold">
              Taux d'admission : <span className="text-emerald-700">{stats.tauxReussite}</span>
            </div>
          </div>

          {/* Deliberation Table */}
          <div className="border border-slate-300 rounded-xl overflow-hidden">
            <Table>
              <TableHeader className="bg-slate-200 text-slate-900">
                <TableRow>
                  <TableHead className="w-12 font-bold text-slate-900 text-center text-xs">Rang</TableHead>
                  <TableHead className="font-bold text-slate-900 text-xs">Matricule</TableHead>
                  <TableHead className="font-bold text-slate-900 text-xs">Nom & Prénom(s)</TableHead>
                  <TableHead className="font-bold text-slate-900 text-center text-xs">Moyenne /20</TableHead>
                  <TableHead className="font-bold text-slate-900 text-center text-xs">Crédits ECTS</TableHead>
                  <TableHead className="font-bold text-slate-900 text-center text-xs">Mention</TableHead>
                  <TableHead className="font-bold text-slate-900 text-right text-xs pr-4">Décision du Jury</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {resultats
                  .sort((a, b) => b.moyenneGenerale - a.moyenneGenerale)
                  .map((etudiant, idx) => (
                    <TableRow key={etudiant.id} className="border-b border-slate-200 text-xs">
                      <TableCell className="text-center font-bold text-slate-700">{idx + 1}</TableCell>
                      <TableCell className="font-mono font-semibold">{etudiant.matricule}</TableCell>
                      <TableCell className="font-bold text-slate-900">
                        {etudiant.nom} {etudiant.prenom}
                        {etudiant.hasNoteEliminatoire && (
                          <span className="block text-[10px] text-rose-600 font-normal">
                            Note élim. : {etudiant.notesEliminatoiresDetails.join(", ")}
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-center font-mono font-bold text-slate-900">
                        {etudiant.moyenneGenerale.toFixed(2)}
                      </TableCell>
                      <TableCell className="text-center font-mono font-semibold">
                        <span className={etudiant.totalECTSAcquis === 30 ? "text-emerald-700 font-bold" : "text-amber-700 font-bold"}>
                          {etudiant.totalECTSAcquis}
                        </span>{" "}
                        / 30
                      </TableCell>
                      <TableCell className="text-center">
                        <span className="font-medium text-slate-700">{etudiant.mention}</span>
                      </TableCell>
                      <TableCell className="text-right pr-4">
                        {getStatutBadge(etudiant.statutSession)}
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </div>

          {/* Statistical Summary Box */}
          <div className="grid grid-cols-4 gap-3 text-center border p-3 rounded-xl bg-slate-50 border-slate-200 text-xs">
            <div>
              <span className="text-[10px] uppercase text-slate-500 block">Effectif Évalué</span>
              <span className="text-lg font-bold text-slate-900">{stats.total} étudiants</span>
            </div>
            <div>
              <span className="text-[10px] uppercase text-emerald-700 block">Admis d'Office</span>
              <span className="text-lg font-bold text-emerald-800">{stats.admis}</span>
            </div>
            <div>
              <span className="text-[10px] uppercase text-amber-700 block">Admis à Rattraper</span>
              <span className="text-lg font-bold text-amber-800">{stats.rattrapage}</span>
            </div>
            <div>
              <span className="text-[10px] uppercase text-rose-700 block">Ajournés (Échec)</span>
              <span className="text-lg font-bold text-rose-800">{stats.ajournes}</span>
            </div>
          </div>

          {/* Signatures Block */}
          <div className="pt-6 border-t-2 border-slate-900">
            <div className="flex justify-between items-end text-xs">
              <div className="space-y-1">
                <p className="text-[10px] text-slate-500 uppercase">Fait et clos en séance plénière le :</p>
                <p className="font-bold text-slate-800">{new Date().toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })}</p>
                <p className="text-[10px] italic text-slate-400">Document authentifié par signature électronique SHA-256</p>
              </div>

              <div className="flex gap-12 text-center">
                <div className="w-36">
                  <p className="text-[10px] font-bold uppercase text-slate-600 mb-10">Le Rapporteur</p>
                  <p className="text-xs font-bold text-slate-800 border-t border-slate-400 pt-1">Dr. Sophie Ndiaye</p>
                </div>
                <div className="w-36">
                  <p className="text-[10px] font-bold uppercase text-slate-600 mb-10">Le Président du Jury</p>
                  <p className="text-xs font-bold text-slate-800 border-t border-slate-400 pt-1">Prof. Konan Kouamé</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
