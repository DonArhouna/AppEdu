import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { ShieldCheck, CheckCircle2, QrCode, FileText, Download, Lock, Search, AlertCircle } from "lucide-react";
import logo from "@/assets/logo.svg";

export const VerificationDocument = () => {
  const { id } = useParams<{ id: string }>();
  const [searchDocId, setSearchDocId] = useState(id || "BUL-2026-8849");
  const [searched, setSearched] = useState(true);

  const mockDocData = {
    documentId: searchDocId.toUpperCase(),
    type: "Bulletin Officiel de Notes - Semestre 1",
    etablissement: "Institut Supérieur EduManage (Campus Central)",
    etudiant: "Marie Dupont",
    matricule: "ETU-2026-0042",
    filiere: "Master 1 Génie Logiciel",
    session: "Année Académique 2025-2026",
    moyenne: "15.84 / 20 (Mention Bien)",
    dateEmission: "28 Août 2026",
    hashSHA256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    statut: "Authentifié & Certifié",
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearched(true);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-sidebar/10 via-background to-sidebar/20 p-4 sm:p-8 flex flex-col items-center justify-center">
      <div className="w-full max-w-3xl space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center gap-2 p-2 px-4 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-semibold">
            <ShieldCheck className="h-4 w-4" /> Service Officiel de Vérification d'Authenticité
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
            Vérification de Documents Scolaires
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground">
            Validation contre la falsification des bulletins, diplômes et reçus émis par EduManagePro
          </p>
        </div>

        {/* Search Bar */}
        <Card className="shadow-lg border-border/80">
          <CardContent className="p-4 sm:p-6">
            <form onSubmit={handleSearch} className="flex gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Entrez le code de vérification (ex: BUL-2026-8849)..."
                  value={searchDocId}
                  onChange={(e) => setSearchDocId(e.target.value)}
                  className="pl-9 text-sm"
                />
              </div>
              <Button type="submit" className="shadow-md">
                Vérifier
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Verification Result Card */}
        {searched && (
          <Card className="shadow-2xl border-emerald-500/40 relative overflow-hidden bg-card">
            {/* Top Security Banner */}
            <div className="bg-emerald-600 text-white px-6 py-3 flex items-center justify-between">
              <div className="flex items-center gap-2 font-semibold text-sm">
                <CheckCircle2 className="h-5 w-5 shrink-0" />
                DOCUMENT AUTHENTIQUE & SÉCURISÉ
              </div>
              <Badge className="bg-white/20 text-white border-none text-[10px]">
                Certificat d'Authenticité
              </Badge>
            </div>

            <CardContent className="p-6 sm:p-8 space-y-6">
              {/* Document Details Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 border-b pb-6">
                <div>
                  <span className="text-xs text-muted-foreground uppercase font-bold tracking-wider">
                    Type de Document
                  </span>
                  <p className="text-base font-bold text-foreground mt-0.5">
                    {mockDocData.type}
                  </p>
                  <p className="text-xs text-primary font-medium mt-1">
                    ID: {mockDocData.documentId}
                  </p>
                </div>

                <div>
                  <span className="text-xs text-muted-foreground uppercase font-bold tracking-wider">
                    Établissement Émetteur
                  </span>
                  <p className="text-sm font-semibold text-foreground mt-0.5">
                    {mockDocData.etablissement}
                  </p>
                  <p className="text-xs text-muted-foreground">SaaS EduManagePro Validé</p>
                </div>

                <div>
                  <span className="text-xs text-muted-foreground uppercase font-bold tracking-wider">
                    Étudiant Titulaire
                  </span>
                  <p className="text-base font-bold text-foreground mt-0.5">
                    {mockDocData.etudiant}
                  </p>
                  <p className="text-xs text-muted-foreground">Matricule: {mockDocData.matricule}</p>
                </div>

                <div>
                  <span className="text-xs text-muted-foreground uppercase font-bold tracking-wider">
                    Filière & Session
                  </span>
                  <p className="text-sm font-semibold text-foreground mt-0.5">
                    {mockDocData.filiere}
                  </p>
                  <p className="text-xs text-muted-foreground">{mockDocData.session}</p>
                </div>
              </div>

              {/* Academic Highlights */}
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-200 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div>
                  <span className="text-xs font-semibold text-emerald-800">Résultat Académique Inscrit :</span>
                  <p className="text-lg font-bold text-emerald-900">{mockDocData.moyenne}</p>
                </div>
                <div className="text-right">
                  <span className="text-xs text-emerald-700">Date d'Émission Officielle :</span>
                  <p className="text-xs font-medium text-emerald-900">{mockDocData.dateEmission}</p>
                </div>
              </div>

              {/* Cryptographic Hash Verification */}
              <div className="space-y-1 bg-muted/40 p-3 rounded-lg border text-xs font-mono">
                <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                  <span>Empreinte Numérique SHA-256 (Anti-Modification) :</span>
                  <Lock className="h-3 w-3 text-emerald-600" />
                </div>
                <p className="text-foreground text-[10px] break-all select-all font-mono">
                  {mockDocData.hashSHA256}
                </p>
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
                <Button variant="outline" size="sm" onClick={() => window.print()} className="w-full sm:w-auto">
                  <Download className="h-4 w-4 mr-2" /> Imprimer Attestation de Vérification
                </Button>
                <Link to="/" className="text-xs text-primary hover:underline">
                  Retour à EduManagePro
                </Link>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default VerificationDocument;
