import React, { useState, useMemo } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { KpiCard } from "@/components/ui/kpi-card";
import {
  AlertTriangle,
  Send,
  Printer,
  Search,
  CheckCircle2,
  Clock,
  ShieldAlert,
  Wallet,
  DollarSign,
  Mail,
  MessageSquare,
  FileText,
  Filter,
} from "lucide-react";
import { toast } from "sonner";
import {
  type Debiteur,
  type NiveauRelance,
  type CanalRelance,
  type HistoriqueRelance,
  INITIAL_DEBITEURS,
  MODELES_RELANCE,
  relanceService,
} from "@/services/relanceService";
import { LettreRelanceModal } from "./LettreRelanceModal";

export const BalanceAgee: React.FC = () => {
  const [debiteurs, setDebiteurs] = useState<Debiteur[]>(INITIAL_DEBITEURS);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTranche, setSelectedTranche] = useState<string>("ALL");
  const [historique, setHistorique] = useState<HistoriqueRelance[]>([]);

  // State for letter modal
  const [letterOpen, setLetterOpen] = useState(false);
  const [selectedDebiteurForLetter, setSelectedDebiteurForLetter] = useState<Debiteur | null>(null);

  // State for quick send modal
  const [sendModalOpen, setSendModalOpen] = useState(false);
  const [activeDebiteur, setActiveDebiteur] = useState<Debiteur | null>(null);
  const [selectedNiveau, setSelectedNiveau] = useState<NiveauRelance>("NIVEAU_1");
  const [selectedCanal, setSelectedCanal] = useState<CanalRelance>("EMAIL");
  const [customMessage, setCustomMessage] = useState("");

  // Calculate statistics
  const stats = useMemo(() => relanceService.calculerStats(debiteurs), [debiteurs]);

  // Filter debtors
  const filteredDebiteurs = useMemo(() => {
    return debiteurs.filter((d) => {
      const matchesSearch =
        d.nom.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.prenom.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.matricule.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.numeroFacture.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesTranche =
        selectedTranche === "ALL" ||
        (selectedTranche === "1_30" && d.trancheRetard === "1_30") ||
        (selectedTranche === "31_60" && d.trancheRetard === "31_60") ||
        (selectedTranche === "61_90" && d.trancheRetard === "61_90") ||
        (selectedTranche === "PLUS_90" && d.trancheRetard === "PLUS_90") ||
        (selectedTranche === "CRITIQUE" && (d.trancheRetard === "61_90" || d.trancheRetard === "PLUS_90"));

      return matchesSearch && matchesTranche;
    });
  }, [debiteurs, searchQuery, selectedTranche]);

  // Open send relance modal
  const handleOpenSend = (debiteur: Debiteur) => {
    setActiveDebiteur(debiteur);
    setSelectedNiveau(debiteur.niveauRecommande);
    setSelectedCanal("EMAIL");
    const rawTemplate = MODELES_RELANCE[debiteur.niveauRecommande].emailCorps;
    setCustomMessage(relanceService.interpolerMessage(rawTemplate, debiteur));
    setSendModalOpen(true);
  };

  // Switch level in send modal
  const handleNiveauChange = (niveau: NiveauRelance) => {
    setSelectedNiveau(niveau);
    if (!activeDebiteur) return;
    const raw = selectedCanal === "SMS" ? MODELES_RELANCE[niveau].smsCorps : MODELES_RELANCE[niveau].emailCorps;
    setCustomMessage(relanceService.interpolerMessage(raw, activeDebiteur));
  };

  // Switch channel in send modal
  const handleCanalChange = (canal: CanalRelance) => {
    setSelectedCanal(canal);
    if (!activeDebiteur) return;
    const raw = canal === "SMS" ? MODELES_RELANCE[selectedNiveau].smsCorps : MODELES_RELANCE[selectedNiveau].emailCorps;
    setCustomMessage(relanceService.interpolerMessage(raw, activeDebiteur));
  };

  // Confirm sending relance
  const handleConfirmSend = () => {
    if (!activeDebiteur) return;

    const newRelance = relanceService.envoyerRelance(activeDebiteur, selectedNiveau, selectedCanal);

    // Update debiteur status
    setDebiteurs((prev) =>
      prev.map((d) =>
        d.id === activeDebiteur.id
          ? {
              ...d,
              derniereRelance: {
                date: new Date().toISOString().split("T")[0],
                niveau: selectedNiveau,
                canal: selectedCanal,
              },
            }
          : d
      )
    );

    setHistorique((prev) => [newRelance, ...prev]);
    setSendModalOpen(false);

    toast.success(
      `Relance ${selectedNiveau} transmise avec succès à ${activeDebiteur.prenom} ${activeDebiteur.nom} par ${selectedCanal}.`
    );
  };

  // Open letter modal
  const handleOpenLetter = (debiteur: Debiteur) => {
    setSelectedDebiteurForLetter(debiteur);
    setLetterOpen(true);
  };

  const getTrancheBadge = (tranche: Debiteur["trancheRetard"]) => {
    switch (tranche) {
      case "1_30":
        return <Badge className="bg-blue-600 text-white hover:bg-blue-700">1 à 30 jours</Badge>;
      case "31_60":
        return <Badge className="bg-amber-500 text-white hover:bg-amber-600">31 à 60 jours</Badge>;
      case "61_90":
        return <Badge className="bg-orange-600 text-white hover:bg-orange-700">61 à 90 jours</Badge>;
      case "PLUS_90":
        return <Badge className="bg-rose-600 text-white hover:bg-rose-700">Plus de 90 jours</Badge>;
      default:
        return <Badge variant="outline">À échoir</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* KPI Cards Header */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Total Créances en Retard"
          value={`${stats.totalCreances.toLocaleString("fr-FR")} F`}
          subtitle={`${stats.totalDebiteurs} dossiers débiteurs actifs`}
          icon={Wallet}
          color="rose"
        />
        <KpiCard
          title="Créances Critiques (> 60j)"
          value={`${stats.totalCritique.toLocaleString("fr-FR")} F`}
          subtitle={`${stats.contentieuxCount} dossiers en contentieux lourd`}
          icon={ShieldAlert}
          color="rose"
        />
        <KpiCard
          title="Retard Moyen / 1-30j"
          value={`${stats.tranche1_30.toLocaleString("fr-FR")} F`}
          subtitle="Rappels amiables niveau 1"
          icon={Clock}
          color="amber"
        />
        <KpiCard
          title="Taux Recouvrement Global"
          value="78.4%"
          subtitle="Objectif de gestion : 85%"
          icon={CheckCircle2}
          color="emerald"
        />
      </div>

      {/* Main Aging Table Card */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-amber-500" />
                Balance Âgée des Créances & Procédures de Relance
              </CardTitle>
              <CardDescription>
                Segmentation temporelle des impayés avec automatisation des relances échelonnées (Niveau 1 à 3)
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  const count = debiteurs.filter((d) => !d.derniereRelance).length;
                  toast.success(`Relances groupées automatiques envoyées à ${count || debiteurs.length} débiteurs !`);
                }}
              >
                <Send className="h-4 w-4 mr-1.5" />
                Relance Groupée Automatique
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Filter Bar */}
          <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
            <div className="relative w-full md:w-80">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Rechercher étudiant, matricule, facture..."
                className="pl-8"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            {/* Tranche Buttons */}
            <div className="flex items-center gap-1.5 flex-wrap w-full md:w-auto">
              <Button
                size="sm"
                variant={selectedTranche === "ALL" ? "default" : "outline"}
                onClick={() => setSelectedTranche("ALL")}
              >
                Tous ({debiteurs.length})
              </Button>
              <Button
                size="sm"
                variant={selectedTranche === "1_30" ? "default" : "outline"}
                onClick={() => setSelectedTranche("1_30")}
              >
                1 - 30j
              </Button>
              <Button
                size="sm"
                variant={selectedTranche === "31_60" ? "default" : "outline"}
                onClick={() => setSelectedTranche("31_60")}
              >
                31 - 60j
              </Button>
              <Button
                size="sm"
                variant={selectedTranche === "61_90" ? "default" : "outline"}
                onClick={() => setSelectedTranche("61_90")}
              >
                61 - 90j
              </Button>
              <Button
                size="sm"
                variant={selectedTranche === "PLUS_90" ? "default" : "outline"}
                onClick={() => setSelectedTranche("PLUS_90")}
              >
                &gt; 90j
              </Button>
              <Button
                size="sm"
                variant={selectedTranche === "CRITIQUE" ? "destructive" : "outline"}
                onClick={() => setSelectedTranche("CRITIQUE")}
              >
                Critiques ({stats.contentieuxCount})
              </Button>
            </div>
          </div>

          {/* Table */}
          <div className="rounded-xl border overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40">
                  <TableHead>Étudiant / Matricule</TableHead>
                  <TableHead>Filière</TableHead>
                  <TableHead>Facture Réf.</TableHead>
                  <TableHead className="text-right">Montant Dû</TableHead>
                  <TableHead className="text-center">Jours de Retard</TableHead>
                  <TableHead className="text-center">Tranche</TableHead>
                  <TableHead className="text-center">Dernière Relance</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredDebiteurs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                      Aucun dossier débiteur trouvé pour ce filtre.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredDebiteurs.map((d) => (
                    <TableRow key={d.id} className="hover:bg-muted/30">
                      <TableCell>
                        <div className="font-semibold text-sm">
                          {d.prenom} {d.nom}
                        </div>
                        <div className="font-mono text-xs text-muted-foreground">{d.matricule}</div>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">{d.filiere}</TableCell>
                      <TableCell className="font-mono text-xs font-semibold">{d.numeroFacture}</TableCell>
                      <TableCell className="text-right">
                        <span className="font-mono font-bold text-rose-600 text-sm">
                          {d.montantRestant.toLocaleString("fr-FR")} F
                        </span>
                        <div className="text-[11px] text-muted-foreground">
                          sur {d.montantTotal.toLocaleString("fr-FR")} F
                        </div>
                      </TableCell>
                      <TableCell className="text-center font-mono font-bold text-sm">
                        {d.joursRetard} jours
                      </TableCell>
                      <TableCell className="text-center">{getTrancheBadge(d.trancheRetard)}</TableCell>
                      <TableCell className="text-center">
                        {d.derniereRelance ? (
                          <div className="space-y-0.5">
                            <Badge variant="outline" className="text-[10px] font-mono">
                              {d.derniereRelance.niveau} ({d.derniereRelance.canal})
                            </Badge>
                            <div className="text-[10px] text-muted-foreground">{d.derniereRelance.date}</div>
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground italic">Aucune relance</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-8 px-2.5"
                            onClick={() => handleOpenSend(d)}
                            title="Envoyer relance Email / SMS"
                          >
                            <Send className="h-3.5 w-3.5 mr-1" />
                            Relancer
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-8 px-2 text-primary"
                            onClick={() => handleOpenLetter(d)}
                            title="Imprimer Mise en Demeure / Lettre A4"
                          >
                            <Printer className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Audit Log / Historique récent */}
      {historique.length > 0 && (
        <Card>
          <CardHeader className="py-4">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              Journal des Relances Récentes ({historique.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="py-0 pb-4">
            <div className="divide-y divide-border text-xs">
              {historique.map((h) => (
                <div key={h.id} className="py-2.5 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="font-mono text-[10px]">
                      {h.canal}
                    </Badge>
                    <span className="font-semibold">{h.nomComplet}</span>
                    <span className="text-muted-foreground">({h.matricule})</span>
                    <Badge
                      className={
                        h.niveau === "NIVEAU_3"
                          ? "bg-rose-600 text-white"
                          : h.niveau === "NIVEAU_2"
                          ? "bg-amber-500 text-white"
                          : "bg-blue-600 text-white"
                      }
                    >
                      {h.niveau}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-3 text-muted-foreground font-mono">
                    <span>{h.montantRappele.toLocaleString("fr-FR")} FCFA</span>
                    <Badge className="bg-emerald-600 text-white text-[10px]">{h.statut}</Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Modal d'envoi individuel multi-canal */}
      <Dialog open={sendModalOpen} onOpenChange={setSendModalOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Send className="h-5 w-5 text-primary" />
              Envoyer une Relance de Recouvrement
            </DialogTitle>
            <DialogDescription>
              Destinataire : {activeDebiteur?.prenom} {activeDebiteur?.nom} (Facture {activeDebiteur?.numeroFacture})
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase">
                  Niveau d'Échelonnement
                </label>
                <Select value={selectedNiveau} onValueChange={(val: NiveauRelance) => handleNiveauChange(val)}>
                  <SelectTrigger className="h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="NIVEAU_1">Niveau 1 — Amiable / Courtois (1-30j)</SelectItem>
                    <SelectItem value="NIVEAU_2">Niveau 2 — Ferme / Avertissement (31-60j)</SelectItem>
                    <SelectItem value="NIVEAU_3">Niveau 3 — Mise en Demeure / Contentieux (&gt;60j)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase">Canal de Transmission</label>
                <Select value={selectedCanal} onValueChange={(val: CanalRelance) => handleCanalChange(val)}>
                  <SelectTrigger className="h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="EMAIL">Email Professionnel</SelectItem>
                    <SelectItem value="SMS">SMS Instantané</SelectItem>
                    <SelectItem value="TOUS">Email + SMS combiné</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="p-3 bg-muted/40 rounded-lg border text-xs space-y-1">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Solde Débiteur :</span>
                <span className="font-mono font-bold text-rose-600">
                  {activeDebiteur?.montantRestant.toLocaleString("fr-FR")} FCFA
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Retard Constaté :</span>
                <span className="font-bold">{activeDebiteur?.joursRetard} jours</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Contact :</span>
                <span className="font-mono">
                  {activeDebiteur?.email} • {activeDebiteur?.telephone}
                </span>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground uppercase">
                Aperçu & Personnalisation du Message
              </label>
              <Textarea
                rows={6}
                value={customMessage}
                onChange={(e) => setCustomMessage(e.target.value)}
                className="font-mono text-xs leading-relaxed"
              />
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" onClick={() => setSendModalOpen(false)}>
              Annuler
            </Button>
            <Button onClick={handleConfirmSend} className="bg-primary text-primary-foreground">
              <Send className="h-4 w-4 mr-1.5" />
              Confirmer l'Envoi
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Lettre Officielle / Mise en Demeure Modal */}
      <LettreRelanceModal
        open={letterOpen}
        onOpenChange={setLetterOpen}
        debiteur={selectedDebiteurForLetter}
      />
    </div>
  );
};
