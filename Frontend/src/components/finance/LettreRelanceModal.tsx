import React from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Printer, Download, AlertOctagon, Landmark, ShieldAlert, CheckCircle2 } from "lucide-react";
import type { Debiteur, NiveauRelance } from "@/services/relanceService";
import { MODELES_RELANCE } from "@/services/relanceService";

interface LettreRelanceModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  debiteur: Debiteur | null;
  niveau?: NiveauRelance;
}

export const LettreRelanceModal: React.FC<LettreRelanceModalProps> = ({
  open,
  onOpenChange,
  debiteur,
  niveau = debiteur?.niveauRecommande || "NIVEAU_2",
}) => {
  if (!debiteur) return null;

  const currentModele = MODELES_RELANCE[niveau];
  const currentDate = new Date().toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  const handlePrint = () => {
    window.print();
  };

  const isMiseEnDemeure = niveau === "NIVEAU_3";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[92vh] overflow-y-auto p-0 print:p-0 print:max-w-none print:shadow-none print:border-none">
        {/* Modal Top Bar (hidden on print) */}
        <div className="p-4 border-b bg-muted/40 flex items-center justify-between print:hidden">
          <div className="flex items-center gap-2">
            {isMiseEnDemeure ? (
              <ShieldAlert className="h-5 w-5 text-destructive" />
            ) : (
              <Landmark className="h-5 w-5 text-primary" />
            )}
            <div>
              <DialogTitle className="text-base font-semibold">
                {isMiseEnDemeure ? "Mise en Demeure Formelle (Contentieux)" : "Lettre Officielle de Relance"}
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground">
                Document certifié émis pour {debiteur.prenom} {debiteur.nom} ({debiteur.matricule})
              </DialogDescription>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={isMiseEnDemeure ? "destructive" : "outline"} className="uppercase font-mono text-xs">
              {currentModele.ton}
            </Badge>
            <Button size="sm" onClick={handlePrint} className="bg-primary text-primary-foreground">
              <Printer className="h-4 w-4 mr-1.5" /> Imprimer / PDF
            </Button>
          </div>
        </div>

        {/* Printable Document Layout */}
        <div className="p-8 sm:p-12 bg-white text-slate-900 font-sans space-y-6 print:m-0 print:p-6 print:text-black">
          {/* Header & Logo */}
          <div className="flex justify-between items-start border-b border-slate-300 pb-6">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <div className="h-10 w-10 bg-primary/10 text-primary flex items-center justify-center rounded-lg font-bold text-xl border border-primary/20">
                  AE
                </div>
                <div>
                  <h2 className="text-lg font-black tracking-tight text-slate-900 uppercase">
                    Institut Supérieur AppEdu
                  </h2>
                  <p className="text-xs text-slate-500 font-medium">Direction des Affaires Financières & Recouvrement</p>
                </div>
              </div>
              <p className="text-[11px] text-slate-500 pt-2 leading-relaxed">
                Boulevard de l'Université • Campus Central, Bâtiment Finance<br />
                Tél : +225 27 20 00 11 22 • Email : recouvrement@universite.edu
              </p>
            </div>

            <div className="text-right space-y-1">
              <p className="text-xs text-slate-500">Date d'émission :</p>
              <p className="text-sm font-semibold text-slate-900">{currentDate}</p>
              <p className="text-[11px] font-mono text-slate-500">
                Réf : REC/{new Date().getFullYear()}/{debiteur.numeroFacture}
              </p>
            </div>
          </div>

          {/* Destinataire Box */}
          <div className="flex justify-end">
            <div className="w-full sm:w-1/2 p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-1">
              <p className="text-[10px] font-bold uppercase text-slate-400">À l'attention de l'étudiant / Responsable légal :</p>
              <p className="text-sm font-bold text-slate-900">{debiteur.prenom} {debiteur.nom}</p>
              <p className="text-xs text-slate-600">Matricule : <span className="font-mono font-semibold">{debiteur.matricule}</span></p>
              <p className="text-xs text-slate-600">Filière : {debiteur.filiere}</p>
              <p className="text-xs text-slate-600">Contact : {debiteur.telephone} • {debiteur.email}</p>
            </div>
          </div>

          {/* Objet */}
          <div className="py-2 border-y border-slate-200">
            <p className="text-sm font-bold text-slate-900 uppercase tracking-wide">
              Objet : {isMiseEnDemeure ? "MISE EN DEMEURE FORMELLE AVANT CONTENTIEUX" : currentModele.emailObjet.replace(/{{.+?}}/g, "")}
            </p>
            <p className="text-xs text-slate-500 font-medium mt-0.5">
              Facture n° <span className="font-mono font-bold text-slate-800">{debiteur.numeroFacture}</span> — Date d'échéance : <span className="font-semibold text-slate-800">{debiteur.dateEcheance}</span> (Retard constaté : {debiteur.joursRetard} jours)
            </p>
          </div>

          {/* Corps de la lettre */}
          <div className="space-y-4 text-xs sm:text-sm text-slate-700 leading-relaxed">
            <p>Madame, Monsieur,</p>

            {niveau === "NIVEAU_1" && (
              <>
                <p>
                  Sauf erreur ou omission de notre service comptable, nous constatons que la facture visée en référence, relative aux frais de scolarité de l'année académique en cours, présente un solde débiteur non régularisé.
                </p>
                <p>
                  Nous vous remercions de bien vouloir procéder au virement ou au versement à la caisse de l'établissement dans un délai de 8 jours à compter de la réception de la présente.
                </p>
              </>
            )}

            {niveau === "NIVEAU_2" && (
              <>
                <p>
                  Malgré notre précédent avis d'échéance, nos écritures comptables indiquent que votre compte présente toujours un solde impayé de <strong>{debiteur.montantRestant.toLocaleString("fr-FR")} FCFA</strong>.
                </p>
                <p>
                  Nous vous demandons instamment de régulariser cette somme sous un délai impératif de <strong>5 jours ouvrés</strong>. À défaut de régularisation, les dispositions statutaires relatives à la suspension temporaire des accès pédagogiques devront être appliquées.
                </p>
              </>
            )}

            {niveau === "NIVEAU_3" && (
              <>
                <p className="font-semibold text-slate-900">
                  Par la présente notification officielle, nous vous mettons formellement EN DEMEURE de nous régler la somme principale de <strong>{debiteur.montantRestant.toLocaleString("fr-FR")} FCFA</strong> au titre des frais d'inscription et de scolarité demeurés impayés.
                </p>
                <div className="p-3 bg-red-50 border border-red-200 rounded-md text-red-950 font-medium text-xs space-y-1">
                  <p className="font-bold flex items-center gap-1.5 text-red-700">
                    <AlertOctagon className="h-4 w-4" /> Conséquences immédiates à défaut de règlement sous 48 heures :
                  </p>
                  <ul className="list-disc list-inside space-y-0.5 text-slate-800 pl-2">
                    <li>Désactivation de la carte d'étudiant et accès refusé aux salles de cours et examens ;</li>
                    <li>Blocage de la délivrance des relevés de notes officiels, attestations et diplômes ;</li>
                    <li>Transmission du dossier au cabinet d'huissiers / contentieux pour recouvrement judiciaire.</li>
                  </ul>
                </div>
              </>
            )}

            {/* Tableau récapitulatif de la dette */}
            <div className="my-4 border border-slate-200 rounded-lg overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                  <tr>
                    <th className="p-2.5">Désignation</th>
                    <th className="p-2.5 text-right">Montant Facturé</th>
                    <th className="p-2.5 text-right">Acomptes Reçus</th>
                    <th className="p-2.5 text-right text-destructive font-bold">Solde Débiteur</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  <tr>
                    <td className="p-2.5 font-sans font-medium text-slate-800">
                      Scolarité annuelle & Droits pédagogiques ({debiteur.filiere})
                    </td>
                    <td className="p-2.5 text-right">{debiteur.montantTotal.toLocaleString("fr-FR")} FCFA</td>
                    <td className="p-2.5 text-right text-emerald-600 font-semibold">{debiteur.montantPaye.toLocaleString("fr-FR")} FCFA</td>
                    <td className="p-2.5 text-right font-black text-rose-600 text-sm">
                      {debiteur.montantRestant.toLocaleString("fr-FR")} FCFA
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Coordonnées bancaires */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-2">
              <p className="text-xs font-bold uppercase text-slate-700">Coordonnées Bancaires de Règlement :</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-slate-500">Établissement bancaire :</span>{" "}
                  <span className="font-semibold text-slate-800">Société Générale / Banque Atlantique</span>
                </div>
                <div>
                  <span className="text-slate-500">Titulaire :</span>{" "}
                  <span className="font-semibold text-slate-800">Institut Supérieur AppEdu SA</span>
                </div>
                <div className="sm:col-span-2">
                  <span className="text-slate-500">IBAN / RIB :</span>{" "}
                  <span className="font-mono font-bold text-slate-900 bg-white px-2 py-0.5 border rounded">
                    CI059 01001 002345678901 22
                  </span>
                </div>
                <div className="sm:col-span-2 text-[11px] text-slate-500">
                  <span className="font-semibold text-slate-700">Motif obligatoire à indiquer :</span>{" "}
                  {debiteur.matricule} - {debiteur.nom} - {debiteur.numeroFacture}
                </div>
              </div>
            </div>

            <p className="pt-2">
              Nous vous prions d'agréer, Madame, Monsieur, l'expression de nos salutations distinguées.
            </p>
          </div>

          {/* Signature & Cachet */}
          <div className="pt-8 flex justify-between items-end">
            <div className="text-[11px] text-slate-400 font-mono">
              Document généré électroniquement • ID {debiteur.id}
            </div>
            <div className="text-right space-y-2">
              <p className="text-xs font-semibold text-slate-700">Pour la Direction Générale & Financière,</p>
              <div className="h-16 flex items-center justify-end pr-4">
                <div className="border-2 border-dashed border-primary/40 rounded-full px-4 py-2 text-primary font-serif font-black text-xs uppercase tracking-widest rotate-[-5deg]">
                  VISA DIRECTION DAF
                </div>
              </div>
              <p className="text-xs font-bold text-slate-900">Dr. Marcelle Koffi</p>
              <p className="text-[10px] text-slate-500">Directrice Administrative et Financière</p>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
