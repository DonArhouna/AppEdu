/**
 * Bouton d'export de la liste des etudiants.
 *
 * Deux details qui ne vont pas de soi :
 *
 * - l'URL d'objet est **revoquee** apres le clic. Sans cela, chaque export
 *   laisse un blob en memoire pour toute la session ;
 * - le nombre de lignes exportees est annonce. Un fichier qui s'ouvre ne dit
 *   pas s'il contient la promotion entiere ou dix lignes : l'institut doit le
 *   savoir sans l'ouvrir.
 */

import { useState } from "react";
import { Download, FileSpreadsheet, FileText, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { etudiantsExportApi } from "@/services/apiClient";
import { toast } from "sonner";

interface BoutonExportProps {
  /** Restreint l'export a une classe. Absent : tous les etudiants. */
  classeId?: string;
  /** Nom de la classe, pour l'annoncer dans les messages. */
  classeNom?: string | null;
  disabled?: boolean;
}

const Formats = [
  { format: "xlsx" as const, label: "Classeur Excel", icon: FileSpreadsheet },
  { format: "csv" as const, label: "CSV (point-virgule)", icon: FileText },
];

const BoutonExport = ({ classeId, classeNom, disabled }: BoutonExportProps) => {
  const [telechargement, setTelechargement] = useState<string | null>(null);

  const lancer = async (format: "xlsx" | "csv") => {
    setTelechargement(format);
    try {
      const { url, nombre, nomFichier } = await etudiantsExportApi.telecharger({
        classeId,
        format,
      });
      const lien = document.createElement("a");
      lien.href = url;
      lien.download = nomFichier;
      document.body.appendChild(lien);
      lien.click();
      document.body.removeChild(lien);
      URL.revokeObjectURL(url);
      toast.success(
        `${nombre} étudiant(s) exporté(s)${classeNom ? ` — ${classeNom}` : ""}.`
      );
    } catch (erreur) {
      toast.error(
        erreur instanceof Error ? erreur.message : "Export impossible."
      );
    } finally {
      setTelechargement(null);
    }
  };

  const enCours = telechargement !== null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" disabled={disabled || enCours}>
          {enCours ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Download className="mr-2 h-4 w-4" />
          )}
          Exporter
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>
          {classeNom ? `Classe ${classeNom}` : "Tous les étudiants"}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {Formats.map(({ format, label, icon: Icone }) => (
          <DropdownMenuItem
            key={format}
            onSelect={() => void lancer(format)}
            disabled={enCours}
          >
            <Icone className="mr-2 h-4 w-4" />
            {label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default BoutonExport;
