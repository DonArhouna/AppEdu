import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  ShieldAlert,
  Search,
  Filter,
  Download,
  Eye,
  FileText,
  UserCheck,
  CreditCard,
  Edit3,
  Trash2,
  Lock,
  Globe
} from "lucide-react";
import { toast } from "sonner";

interface AuditEntry {
  id: string;
  timestamp: string;
  utilisateur: string;
  role: string;
  action: string;
  categorie: "Scolarité" | "Pédagogie" | "Finances" | "Sécurité" | "Administration";
  ipAddress: string;
  severite: "Normale" | "Sensible" | "Critique";
  details: {
    element: string;
    ancienneValeur?: string;
    nouvelleValeur?: string;
  };
}

const mockAuditLogs: AuditEntry[] = [
  {
    id: "LOG-8941",
    timestamp: "2026-08-28 10:42:15",
    utilisateur: "Marie Dupont",
    role: "Administrateur",
    action: "MODIFICATION_NOTE",
    categorie: "Pédagogie",
    ipAddress: "192.168.1.45",
    severite: "Sensible",
    details: {
      element: "Note Algorithmique - Étudiant Lucas Martin",
      ancienneValeur: "08.5 / 20",
      nouvelleValeur: "14.0 / 20 (Rectification rattrapage)",
    },
  },
  {
    id: "LOG-8940",
    timestamp: "2026-08-28 09:30:00",
    utilisateur: "Amadou Diallo",
    role: "Comptable",
    action: "VALIDATION_PAIEMENT",
    categorie: "Finances",
    ipAddress: "197.234.12.8",
    severite: "Normale",
    details: {
      element: "Reçu de paiement #REC-2026-044",
      ancienneValeur: "En attente de virement",
      nouvelleValeur: "Payé - 450,000 FCFA (Wave Mobile)",
    },
  },
  {
    id: "LOG-8939",
    timestamp: "2026-08-28 08:15:22",
    utilisateur: "Jean-Philippe Kouassi",
    role: "Enseignant",
    action: "VALIDER_BULLETIN",
    categorie: "Pédagogie",
    ipAddress: "160.155.90.14",
    severite: "Sensible",
    details: {
      element: "Bulletin Semestre 1 - Promotion Licence 3 Info",
      ancienneValeur: "Brouillon",
      nouvelleValeur: "Validé et Verrouillé",
    },
  },
  {
    id: "LOG-8938",
    timestamp: "2026-08-27 18:05:40",
    utilisateur: "Système Automatique",
    role: "Système",
    action: "CONNEXION_SUSPECTE",
    categorie: "Sécurité",
    ipAddress: "45.12.98.11",
    severite: "Critique",
    details: {
      element: "Tentative de connexion échouée (3 essais)",
      ancienneValeur: "Compte: admin@edumanagepro.com",
      nouvelleValeur: "IP Bloquée temporairement (15 min)",
    },
  },
  {
    id: "LOG-8937",
    timestamp: "2026-08-27 15:20:10",
    utilisateur: "Sophie Bernard",
    role: "Secrétariat",
    action: "VALIDATION_INSCRIPTION",
    categorie: "Scolarité",
    ipAddress: "192.168.1.12",
    severite: "Normale",
    details: {
      element: "Dossier #DOS-2026-112 - Marie Dupont",
      ancienneValeur: "En attente de pièces requises",
      nouvelleValeur: "Dossier Validé & Carte Établie",
    },
  },
];

const JournalAudit = () => {
  const [logs] = useState<AuditEntry[]>(mockAuditLogs);
  const [search, setSearch] = useState("");
  const [catFilter, setCatFilter] = useState("ALL");
  const [sevFilter, setSevFilter] = useState("ALL");
  const [selectedEntry, setSelectedEntry] = useState<AuditEntry | null>(null);

  const filteredLogs = logs.filter((log) => {
    const matchesSearch =
      log.utilisateur.toLowerCase().includes(search.toLowerCase()) ||
      log.action.toLowerCase().includes(search.toLowerCase()) ||
      log.id.toLowerCase().includes(search.toLowerCase()) ||
      log.details.element.toLowerCase().includes(search.toLowerCase());

    const matchesCat = catFilter === "ALL" || log.categorie === catFilter;
    const matchesSev = sevFilter === "ALL" || log.severite === sevFilter;

    return matchesSearch && matchesCat && matchesSev;
  });

  const getSeveriteBadge = (sev: string) => {
    switch (sev) {
      case "Critique":
        return <Badge className="bg-rose-500/15 text-rose-700 border-rose-300">Critique</Badge>;
      case "Sensible":
        return <Badge className="bg-amber-500/15 text-amber-700 border-amber-300">Sensible</Badge>;
      default:
        return <Badge className="bg-blue-500/15 text-blue-700 border-blue-300">Normale</Badge>;
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground flex items-center gap-3">
            <ShieldAlert className="h-8 w-8 text-rose-500" />
            Journal d'Audit & Piste de Contrôle
          </h1>
          <p className="text-muted-foreground mt-1">
            Traçabilité immuable des actions sensibles, modifications de notes et règlements financiers
          </p>
        </div>

        <Button
          variant="outline"
          onClick={() => toast.info("Génération du rapport d'audit au format PDF/CSV...")}
          className="shadow-sm"
        >
          <Download className="h-4 w-4 mr-2" />
          Exporter l'Audit
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4 sm:p-6 space-y-4">
          <div className="flex flex-col md:flex-row gap-4 justify-between items-center">
            <div className="relative w-full md:w-80">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Rechercher par utilisateur, action, ID..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 text-sm"
              />
            </div>

            <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
              <Select value={catFilter} onValueChange={setCatFilter}>
                <SelectTrigger className="w-[160px] text-xs">
                  <Filter className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                  <SelectValue placeholder="Catégorie" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">Toutes catégories</SelectItem>
                  <SelectItem value="Scolarité">Scolarité</SelectItem>
                  <SelectItem value="Pédagogie">Pédagogie</SelectItem>
                  <SelectItem value="Finances">Finances</SelectItem>
                  <SelectItem value="Sécurité">Sécurité</SelectItem>
                  <SelectItem value="Administration">Administration</SelectItem>
                </SelectContent>
              </Select>

              <Select value={sevFilter} onValueChange={setSevFilter}>
                <SelectTrigger className="w-[150px] text-xs">
                  <SelectValue placeholder="Sévérité" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">Toutes sévérités</SelectItem>
                  <SelectItem value="Normale">Normale</SelectItem>
                  <SelectItem value="Sensible">Sensible</SelectItem>
                  <SelectItem value="Critique">Critique</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Audit Logs Table */}
          <div className="rounded-lg border overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50">
                  <TableHead>Horodatage & ID</TableHead>
                  <TableHead>Utilisateur & Rôle</TableHead>
                  <TableHead>Action Exécutée</TableHead>
                  <TableHead>Catégorie</TableHead>
                  <TableHead>Adresse IP</TableHead>
                  <TableHead>Sévérité</TableHead>
                  <TableHead className="text-right">Détails</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredLogs.map((log) => (
                  <TableRow key={log.id} className="hover:bg-muted/30">
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="font-mono text-xs font-bold text-foreground">
                          {log.id}
                        </span>
                        <span className="text-[11px] text-muted-foreground">{log.timestamp}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="font-medium text-sm">{log.utilisateur}</span>
                        <span className="text-xs text-muted-foreground">{log.role}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="font-mono text-[11px]">
                        {log.action}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs font-medium">{log.categorie}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {log.ipAddress}
                    </TableCell>
                    <TableCell>{getSeveriteBadge(log.severite)}</TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedEntry(log)}
                        className="h-8 px-2 text-xs"
                      >
                        <Eye className="h-3.5 w-3.5 mr-1" /> Inspecter
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Inspector Modal */}
      {selectedEntry && (
        <Dialog open={!!selectedEntry} onOpenChange={() => setSelectedEntry(null)}>
          <DialogContent className="sm:max-w-[550px]">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 font-mono text-base">
                <FileText className="h-5 w-5 text-primary" />
                Inspection du Journal #{selectedEntry.id}
              </DialogTitle>
              <DialogDescription>
                Détails exacts de la modification enregistrée par la piste d'audit.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              <div className="grid grid-cols-2 gap-4 text-xs bg-muted/40 p-3 rounded-lg border">
                <div>
                  <span className="text-muted-foreground">Utilisateur:</span>
                  <p className="font-semibold text-foreground">{selectedEntry.utilisateur}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Horodatage:</span>
                  <p className="font-semibold text-foreground">{selectedEntry.timestamp}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">IP & Réseau:</span>
                  <p className="font-mono text-foreground">{selectedEntry.ipAddress}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Niveau d'Alerte:</span>
                  <p>{getSeveriteBadge(selectedEntry.severite)}</p>
                </div>
              </div>

              <div className="space-y-2">
                <span className="text-xs font-semibold text-foreground">Élément Modifié :</span>
                <p className="text-xs font-medium p-2.5 rounded-md bg-secondary/10 border text-secondary-foreground">
                  {selectedEntry.details.element}
                </p>
              </div>

              {selectedEntry.details.ancienneValeur && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-200">
                    <span className="font-semibold text-rose-700 block mb-1">Valeur Précédente</span>
                    <span className="font-mono text-rose-900">{selectedEntry.details.ancienneValeur}</span>
                  </div>

                  <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-200">
                    <span className="font-semibold text-emerald-700 block mb-1">Nouvelle Valeur</span>
                    <span className="font-mono text-emerald-900">{selectedEntry.details.nouvelleValeur}</span>
                  </div>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

export default JournalAudit;
