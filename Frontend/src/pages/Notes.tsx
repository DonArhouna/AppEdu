import { useState, useMemo } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { FileText, Download, Calculator, ShieldCheck, Eye, Award, CheckCircle2, AlertTriangle, Users, GraduationCap } from "lucide-react";
import { toast } from "sonner";
import { BulletinModal } from "@/components/pedagogie/BulletinModal";
import { PVJuryModal } from "@/components/pedagogie/PVJuryModal";
import { KpiCard } from "@/components/ui/kpi-card";
import {
  deliberationEngine,
  DEFAULT_DELIBERATION_CONFIG,
  MOCK_ETUDIANTS_PROMOTION,
  type DeliberationConfig,
} from "@/services/deliberationEngine";

export default function Notes() {
  const [bulletinOpen, setBulletinOpen] = useState(false);
  const [pvOpen, setPvOpen] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState<{ name: string; matricule: string }>({
    name: "Amadou Ba",
    matricule: "ET2024001",
  });

  // Deliberation parameters state
  const [delibConfig, setDelibConfig] = useState<DeliberationConfig>(DEFAULT_DELIBERATION_CONFIG);
  const [hasDeliberated, setHasDeliberated] = useState(true);

  // Compute live deliberation results based on config
  const deliberationResult = useMemo(() => {
    return deliberationEngine.calculerPromotion(MOCK_ETUDIANTS_PROMOTION, delibConfig);
  }, [delibConfig]);

  const [notes, setNotes] = useState([
    { id: "1", etudiant: "Amadou Ba", matricule: "ET2024001", note: 15, coef: 3, statut: "Validé" },
    { id: "2", etudiant: "Fatou Sarr", matricule: "ET2024002", note: 17, coef: 3, statut: "Validé" },
    { id: "3", etudiant: "Ibrahima Diop", matricule: "ET2024003", note: 8.5, coef: 3, statut: "Rattrapage" },
    { id: "4", etudiant: "Awa Ndiaye", matricule: "ET2024004", note: 14, coef: 3, statut: "Validé" },
  ]);

  const calculerMoyenne = () => {
    const total = notes.reduce((acc, n) => acc + n.note * n.coef, 0);
    const totalCoef = notes.reduce((acc, n) => acc + n.coef, 0);
    return (total / totalCoef).toFixed(2);
  };

  const handleNoteChange = (id: string, value: string) => {
    const note = parseFloat(value);
    if (!isNaN(note) && note >= 0 && note <= 20) {
      setNotes(notes.map((n) => (n.id === id ? { ...n, note, statut: note >= 10 ? "Validé" : "Rattrapage" } : n)));
    }
  };

  const getNoteBadge = (note: number) => {
    if (note >= 16) return <Badge className="bg-emerald-600 text-white">Excellent</Badge>;
    if (note >= 14) return <Badge className="bg-primary text-primary-foreground">Bien</Badge>;
    if (note >= 12) return <Badge className="bg-secondary text-secondary-foreground">Assez Bien</Badge>;
    if (note >= 10) return <Badge className="bg-amber-500 text-white">Passable</Badge>;
    return <Badge className="bg-destructive text-destructive-foreground">Rattrapage</Badge>;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Carnet de Notes & Evaluatifs LMD</h1>
          <p className="text-muted-foreground mt-1">
            Saisie des évaluations, délibérations du jury et génération des bulletins officiels
          </p>
        </div>
        <Button
          onClick={() => {
            setSelectedStudent({ name: "Marie Dupont", matricule: "ETU-2026-0042" });
            setBulletinOpen(true);
          }}
          className="bg-emerald-600 hover:bg-emerald-700 text-white shadow-md"
        >
          <FileText className="mr-2 h-4 w-4" />
          Aperçu Bulletin Officiel
        </Button>
      </div>

      <Tabs defaultValue="saisie" className="space-y-6">
        <TabsList>
          <TabsTrigger value="saisie">Saisie des Notes</TabsTrigger>
          <TabsTrigger value="bulletins">Génération des Bulletins LMD</TabsTrigger>
          <TabsTrigger value="deliberation">PV & Délibérations du Jury</TabsTrigger>
        </TabsList>

        {/* Tab 1: Saisie des Notes */}
        <TabsContent value="saisie" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Sélection de la Classe & Matière</CardTitle>
              <CardDescription>Choisir la matière et la session d'évaluation</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col md:flex-row gap-4">
                <Select defaultValue="inf301">
                  <SelectTrigger className="w-full md:w-[250px]">
                    <SelectValue placeholder="Matière" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="inf301">INF301 - Programmation Web</SelectItem>
                    <SelectItem value="inf302">INF302 - Base de données</SelectItem>
                    <SelectItem value="inf303">INF303 - Algorithmique</SelectItem>
                  </SelectContent>
                </Select>
                <Select defaultValue="cc1">
                  <SelectTrigger className="w-full md:w-[200px]">
                    <SelectValue placeholder="Session" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="cc1">Contrôle Continu 1</SelectItem>
                    <SelectItem value="cc2">Contrôle Continu 2</SelectItem>
                    <SelectItem value="examen">Examen Final (Session Normale)</SelectItem>
                    <SelectItem value="rattrapage">Examen de Rattrapage</SelectItem>
                  </SelectContent>
                </Select>
                <Select defaultValue="l1_gl">
                  <SelectTrigger className="w-full md:w-[250px]">
                    <SelectValue placeholder="Classe / Niveau" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="l1_gl">L1 Génie Logiciel</SelectItem>
                    <SelectItem value="l2_gl">L2 Génie Logiciel</SelectItem>
                    <SelectItem value="l3_gl">L3 Génie Logiciel</SelectItem>
                    <SelectItem value="m1_gl">Master 1 Génie Logiciel</SelectItem>
                    <SelectItem value="l1_market">L1 Marketing</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Grille de Notation</CardTitle>
                  <CardDescription>Master 1 Génie Logiciel - Programmation Web (Coef. 3)</CardDescription>
                </div>
                <div className="flex items-center gap-2 text-sm bg-primary/10 px-3 py-1.5 rounded-lg border border-primary/20">
                  <Calculator className="h-4 w-4 text-primary" />
                  <span className="text-muted-foreground">Moyenne de classe:</span>
                  <span className="font-bold text-xl text-primary">{calculerMoyenne()}/20</span>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="rounded-md border border-border overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead>Matricule</TableHead>
                      <TableHead>Étudiant</TableHead>
                      <TableHead className="w-[150px]">Note / 20</TableHead>
                      <TableHead>Coefficient</TableHead>
                      <TableHead>Mention / Statut</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {notes.map((n) => (
                      <TableRow key={n.id} className="hover:bg-accent/50">
                        <TableCell className="font-mono text-xs">{n.matricule}</TableCell>
                        <TableCell className="font-medium">{n.etudiant}</TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            min="0"
                            max="20"
                            step="0.5"
                            value={n.note}
                            onChange={(e) => handleNoteChange(n.id, e.target.value)}
                            className="w-[100px] font-bold"
                          />
                        </TableCell>
                        <TableCell>{n.coef}</TableCell>
                        <TableCell>{getNoteBadge(n.note)}</TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setSelectedStudent({ name: n.etudiant, matricule: n.matricule });
                              setBulletinOpen(true);
                            }}
                          >
                            <Eye className="h-3.5 w-3.5 mr-1" /> Bulletin
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <div className="flex justify-end gap-2 mt-4">
                <Button variant="outline" onClick={() => toast.info("Format Excel téléchargé pour saisie.")}>
                  <Download className="mr-2 h-4 w-4" />
                  Télécharger Modèle Excel
                </Button>
                <Button 
                  variant="outline" 
                  className="bg-blue-50 hover:bg-blue-100 border-blue-200 text-blue-700 dark:bg-blue-900/20 dark:border-blue-800 dark:text-blue-300"
                  onClick={() => {
                    const input = document.createElement("input");
                    input.type = "file";
                    input.accept = ".xlsx, .xls, .csv";
                    input.onchange = () => toast.success("Notes importées avec succès depuis Excel !");
                    input.click();
                  }}
                >
                  Importer Notes (Excel)
                </Button>
                <Button variant="outline" onClick={() => toast.info("Exportation Excel du relevé de notes...")}>
                  <Download className="mr-2 h-4 w-4" />
                  Exporter Relevé
                </Button>
                <Button onClick={() => toast.success("Toutes les notes ont été validées et verrouillées.")}>
                  Enregistrer & Verrouiller
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 2: Bulletins LMD */}
        <TabsContent value="bulletins" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Génération Groupée des Bulletins de Notes</CardTitle>
              <CardDescription>
                Émission massive des bulletins officiels signés numériquement avec QR Code de vérification
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 rounded-xl bg-muted/40 border flex flex-col sm:flex-row items-center justify-between gap-4">
                <div>
                  <p className="font-semibold text-sm">Promotion Master 1 Génie Logiciel (35 Étudiants)</p>
                  <p className="text-xs text-muted-foreground">Semestre 1 • Année Académique 2025-2026</p>
                </div>
                <Button
                  onClick={() => {
                    toast.success("Génération des 35 bulletins terminée. Envoi par email activé.");
                  }}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                >
                  <FileText className="mr-2 h-4 w-4" /> Générer Tous les Bulletins PDF
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 3: Délibérations du Jury */}
        <TabsContent value="deliberation" className="space-y-6">
          {/* Deliberation Rules & Settings Card */}
          <Card>
            <CardHeader>
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Award className="h-5 w-5 text-amber-500" />
                    Moteur de Délibération LMD & Procès-Verbal de Jury
                  </CardTitle>
                  <CardDescription>
                    Promotion Master 1 Génie Logiciel — Semestre 1 (30 ECTS au programme)
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    onClick={() => {
                      toast.loading("Calcul des moyennes et délibération en cours...", { duration: 1200 });
                      setTimeout(() => {
                        setHasDeliberated(true);
                        toast.success("Délibération recalculée avec succès selon les critères LMD définis.");
                      }, 1200);
                    }}
                    className="bg-primary text-primary-foreground shadow-sm"
                  >
                    <Calculator className="mr-2 h-4 w-4" />
                    Lancer la Délibération
                  </Button>
                  <Button
                    onClick={() => setPvOpen(true)}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm"
                  >
                    <ShieldCheck className="mr-2 h-4 w-4" />
                    Générer le PV Officiel
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Parameters Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 p-4 border rounded-xl bg-muted/20">
                <div className="space-y-2">
                  <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Moyenne de Validation (/20)
                  </label>
                  <Input
                    type="number"
                    step="0.25"
                    min="8"
                    max="14"
                    value={delibConfig.seuilValidationMoyenne}
                    onChange={(e) =>
                      setDelibConfig({ ...delibConfig, seuilValidationMoyenne: parseFloat(e.target.value) || 10 })
                    }
                    className="h-9 font-semibold"
                  />
                  <p className="text-[11px] text-muted-foreground">Standard LMD : 10.00/20</p>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Seuil Éliminatoire (/20)
                  </label>
                  <Input
                    type="number"
                    step="0.5"
                    min="5"
                    max="10"
                    value={delibConfig.seuilEliminatoire}
                    onChange={(e) =>
                      setDelibConfig({ ...delibConfig, seuilEliminatoire: parseFloat(e.target.value) || 7 })
                    }
                    className="h-9 font-semibold"
                  />
                  <p className="text-[11px] text-muted-foreground">Toute note inférieure envoie au rattrapage</p>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    ECTS Min. Conditionnel
                  </label>
                  <Input
                    type="number"
                    step="1"
                    min="10"
                    max="28"
                    value={delibConfig.seuilPassageConditionnelECTS}
                    onChange={(e) =>
                      setDelibConfig({ ...delibConfig, seuilPassageConditionnelECTS: parseInt(e.target.value) || 18 })
                    }
                    className="h-9 font-semibold"
                  />
                  <p className="text-[11px] text-muted-foreground">Seuil minimum pour passage sous réserve</p>
                </div>

                <div className="space-y-2 flex flex-col justify-between">
                  <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Compensation Inter-UE
                  </label>
                  <div className="flex items-center justify-between pt-1">
                    <span className="text-sm font-medium">
                      {delibConfig.compensationAutorisee ? "Activée" : "Désactivée"}
                    </span>
                    <Switch
                      checked={delibConfig.compensationAutorisee}
                      onCheckedChange={(checked) =>
                        setDelibConfig({ ...delibConfig, compensationAutorisee: checked })
                      }
                    />
                  </div>
                  <p className="text-[11px] text-muted-foreground">Si moyenne semestrielle ≥ 10/20</p>
                </div>
              </div>

              {/* KPI Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KpiCard
                  title="Taux de Réussite"
                  value={deliberationResult.stats.tauxReussite}
                  subtitle={`Moyenne Promo: ${deliberationResult.stats.moyennePromo}/20`}
                  icon={GraduationCap}
                  color="emerald"
                />
                <KpiCard
                  title="Étudiants Admis"
                  value={deliberationResult.stats.admis}
                  subtitle="Validation immédiate du semestre"
                  icon={CheckCircle2}
                  color="emerald"
                />
                <KpiCard
                  title="Session Rattrapage"
                  value={deliberationResult.stats.rattrapage}
                  subtitle="Matières ou éliminatoires à rattraper"
                  icon={AlertTriangle}
                  color="amber"
                />
                <KpiCard
                  title="Ajournés (Échec)"
                  value={deliberationResult.stats.ajournes}
                  subtitle="ECTS insuffisants pour compensation"
                  icon={Users}
                  color="rose"
                />
              </div>

              {/* Cohort Deliberation Results Table */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-foreground">
                    Résultats Nominatifs de la Promotion ({deliberationResult.resultats.length} étudiants)
                  </h3>
                  <Badge variant="outline" className="font-mono text-xs">
                    Année 2025-2026 • S1
                  </Badge>
                </div>

                <div className="rounded-xl border overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/40">
                        <TableHead>Matricule</TableHead>
                        <TableHead>Étudiant</TableHead>
                        <TableHead className="text-center">ECTS Validés</TableHead>
                        <TableHead className="text-center">Moyenne Générale</TableHead>
                        <TableHead className="text-center">Décision Jury</TableHead>
                        <TableHead className="text-center">Mention</TableHead>
                        <TableHead>Observations / Notes Éliminatoires</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {deliberationResult.resultats.map((etudiant) => (
                        <TableRow key={etudiant.id} className="hover:bg-muted/30">
                          <TableCell className="font-mono text-xs font-semibold">{etudiant.matricule}</TableCell>
                          <TableCell className="font-medium">
                            {etudiant.prenom} {etudiant.nom}
                          </TableCell>
                          <TableCell className="text-center">
                            <span className="font-mono font-bold">
                              {etudiant.totalECTSAcquis}/{etudiant.totalECTSMax}
                            </span>
                          </TableCell>
                          <TableCell className="text-center">
                            <span
                              className={`font-mono font-bold text-sm ${
                                etudiant.moyenneGenerale >= 10 ? "text-emerald-700" : "text-rose-600"
                              }`}
                            >
                              {etudiant.moyenneGenerale.toFixed(2)}/20
                            </span>
                          </TableCell>
                          <TableCell className="text-center">
                            {etudiant.statutSession === "Admis" && (
                              <Badge className="bg-emerald-600 hover:bg-emerald-700 text-white">ADMIS</Badge>
                            )}
                            {etudiant.statutSession === "Rattrapage" && (
                              <Badge className="bg-amber-500 hover:bg-amber-600 text-white">RATTRAPAGE</Badge>
                            )}
                            {etudiant.statutSession === "Ajourné" && (
                              <Badge className="bg-rose-600 hover:bg-rose-700 text-white">AJOURNÉ</Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-center">
                            <Badge variant="outline" className="text-xs">
                              {etudiant.mention}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {etudiant.hasNoteEliminatoire ? (
                              <span className="inline-flex items-center text-xs text-rose-600 font-medium">
                                <AlertTriangle className="h-3.5 w-3.5 mr-1" />
                                Note &lt; {delibConfig.seuilEliminatoire} : {etudiant.notesEliminatoiresDetails.join(", ")}
                              </span>
                            ) : etudiant.ues.some((u) => u.valideeParCompensation) ? (
                              <span className="text-xs text-blue-600 font-medium">
                                Validé par compensation semestrielle
                              </span>
                            ) : (
                              <span className="text-xs text-muted-foreground">Aucune anomalie</span>
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedStudent({
                                  name: `${etudiant.prenom} ${etudiant.nom}`,
                                  matricule: etudiant.matricule,
                                });
                                setBulletinOpen(true);
                              }}
                            >
                              <Eye className="h-3.5 w-3.5 mr-1" /> Bulletin
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row justify-end gap-3 pt-2">
                <Button
                  variant="outline"
                  onClick={() => toast.info("Exportation du relevé de délibération au format Excel...")}
                >
                  <Download className="mr-2 h-4 w-4" />
                  Exporter PV Excel
                </Button>
                <Button
                  onClick={() => setPvOpen(true)}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white shadow-md"
                >
                  <ShieldCheck className="mr-2 h-4 w-4" />
                  Visualiser & Imprimer le Procès-Verbal Signé
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Bulletin Modal */}
      <BulletinModal
        open={bulletinOpen}
        onOpenChange={setBulletinOpen}
        studentName={selectedStudent.name}
        matricule={selectedStudent.matricule}
      />

      {/* PV de Jury Modal */}
      <PVJuryModal
        open={pvOpen}
        onOpenChange={setPvOpen}
        promotionName="Master 1 Génie Logiciel"
        semestre="Semestre 1"
        anneeAcademique="2025-2026"
        resultats={deliberationResult.resultats}
        config={delibConfig}
        stats={deliberationResult.stats}
      />
    </div>
  );
}
