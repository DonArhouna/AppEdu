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
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Mail, MessageSquare, Save, Sparkles, Check } from "lucide-react";
import { notificationService, type NotificationTemplate } from "@/services/notificationService";
import { toast } from "sonner";

interface NotificationTemplateEditorProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaveSuccess?: () => void;
}

export const NotificationTemplateEditor = ({
  open,
  onOpenChange,
  onSaveSuccess,
}: NotificationTemplateEditorProps) => {
  const [templates, setTemplates] = useState<Record<string, NotificationTemplate>>(() =>
    notificationService.getTemplates()
  );

  const [activeStatut, setActiveStatut] = useState<string>("pieces_manquantes");

  const statutsList = [
    { key: "recue", label: "1. Reçue", badge: "Nouvelle" },
    { key: "examen", label: "2. En examen", badge: "Pédagogique" },
    { key: "pieces_manquantes", label: "3. Pièces manquantes", badge: "Action requise" },
    { key: "admis", label: "4. Admis", badge: "Félicitations" },
    { key: "inscrit", label: "5. Inscrit", badge: "Définitif" },
  ];

  const currentTemplate = templates[activeStatut] || {
    statut: activeStatut,
    titre: "Notification",
    emailSubject: "",
    emailBody: "",
    smsBody: "",
  };

  const handleUpdate = (field: keyof NotificationTemplate, value: string) => {
    setTemplates((prev) => ({
      ...prev,
      [activeStatut]: {
        ...currentTemplate,
        [field]: value,
      },
    }));
  };

  const handleSaveAll = () => {
    notificationService.saveTemplates(templates);
    toast.success("Modèles de notifications SMS & Email enregistrés !");
    if (onSaveSuccess) onSaveSuccess();
    onOpenChange(false);
  };

  const insertVariable = (variable: string, field: "emailBody" | "smsBody") => {
    const current = currentTemplate[field] || "";
    handleUpdate(field, `${current} ${variable}`);
  };

  const previewVariables = {
    prenom: "Marie",
    nom: "Dupont",
    filiere: "Master 1 Génie Logiciel",
    pieces_manquantes: "Attestation de réussite Licence, 2 photos d'identité",
    etablissement: "Institut Sup. EduManagePro",
    annee: "2025-2026",
  };

  const previewEmail = notificationService.renderTemplate(currentTemplate.emailBody, previewVariables);
  const previewSms = notificationService.renderTemplate(currentTemplate.smsBody, previewVariables);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[780px] max-h-[90vh] overflow-y-auto rounded-2xl scrollbar-thin">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-amber-500" />
            Éditeur des Modèles de Notifications d'Admission
          </DialogTitle>
          <DialogDescription>
            Personnalisez les messages automatiques envoyés aux candidats à chaque étape de leur parcours d'inscription.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Status selector pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-thin">
            {statutsList.map((st) => (
              <button
                key={st.key}
                type="button"
                onClick={() => setActiveStatut(st.key)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 ${
                  activeStatut === st.key
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground"
                }`}
              >
                <span>{st.label}</span>
                <span className="text-[9px] opacity-80 uppercase">({st.badge})</span>
              </button>
            ))}
          </div>

          {/* Variable insertion helpers */}
          <div className="p-3 rounded-xl bg-muted/30 border border-border/70 space-y-1.5">
            <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block">
              Variables dynamiques disponibles (cliquez pour insérer) :
            </span>
            <div className="flex flex-wrap gap-1.5">
              {[
                { tag: "{{prenom}}", desc: "Prénom du candidat" },
                { tag: "{{nom}}", desc: "Nom de famille" },
                { tag: "{{filiere}}", desc: "Filière choisie" },
                { tag: "{{pieces_manquantes}}", desc: "Liste des pièces manquantes" },
                { tag: "{{etablissement}}", desc: "Nom de l'institut" },
                { tag: "{{annee}}", desc: "Année académique" },
              ].map((v) => (
                <button
                  key={v.tag}
                  type="button"
                  onClick={() => insertVariable(v.tag, "emailBody")}
                  className="px-2 py-0.5 rounded-md bg-background border text-[11px] font-mono hover:bg-primary/10 hover:text-primary transition-colors"
                  title={v.desc}
                >
                  {v.tag}
                </button>
              ))}
            </div>
          </div>

          {/* Email & SMS tabs */}
          <Tabs defaultValue="email" className="space-y-4">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="email" className="flex items-center gap-2">
                <Mail className="h-4 w-4 text-blue-500" />
                Modèle Email
              </TabsTrigger>
              <TabsTrigger value="sms" className="flex items-center gap-2">
                <MessageSquare className="h-4 w-4 text-emerald-500" />
                Modèle SMS
              </TabsTrigger>
            </TabsList>

            {/* Email tab */}
            <TabsContent value="email" className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="emailSubject" className="text-xs font-semibold text-muted-foreground uppercase">
                  Objet du courriel *
                </Label>
                <Input
                  id="emailSubject"
                  value={currentTemplate.emailSubject}
                  onChange={(e) => handleUpdate("emailSubject", e.target.value)}
                  className="h-10 rounded-xl font-medium text-sm"
                  placeholder="Objet de l'email..."
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="emailBody" className="text-xs font-semibold text-muted-foreground uppercase">
                  Corps du message Email *
                </Label>
                <Textarea
                  id="emailBody"
                  value={currentTemplate.emailBody}
                  onChange={(e) => handleUpdate("emailBody", e.target.value)}
                  rows={6}
                  className="rounded-xl font-sans text-sm leading-relaxed"
                  placeholder="Rédigez le texte du courriel..."
                />
              </div>

              {/* Live Preview Box */}
              <div className="p-3.5 rounded-xl bg-blue-50/50 dark:bg-blue-950/20 border border-blue-200/60 dark:border-blue-800/40">
                <span className="text-[10px] font-bold uppercase tracking-wider text-blue-700 dark:text-blue-300 block mb-1">
                  Aperçu du rendu final (Email envoyé à {previewVariables.prenom}) :
                </span>
                <p className="text-xs font-semibold text-foreground">{currentTemplate.emailSubject}</p>
                <p className="text-xs text-muted-foreground whitespace-pre-line mt-1.5 leading-relaxed">
                  {previewEmail}
                </p>
              </div>
            </TabsContent>

            {/* SMS tab */}
            <TabsContent value="sms" className="space-y-3">
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="smsBody" className="text-xs font-semibold text-muted-foreground uppercase">
                    Texte du SMS *
                  </Label>
                  <span className="text-[11px] font-mono text-muted-foreground">
                    {currentTemplate.smsBody.length} caractères (1 SMS ≈ 160 car.)
                  </span>
                </div>
                <Textarea
                  id="smsBody"
                  value={currentTemplate.smsBody}
                  onChange={(e) => handleUpdate("smsBody", e.target.value)}
                  rows={3}
                  className="rounded-xl font-sans text-sm"
                  placeholder="Message SMS direct..."
                />
              </div>

              {/* Live Preview Box */}
              <div className="p-3.5 rounded-xl bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200/60 dark:border-emerald-800/40">
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-300 block mb-1">
                  Aperçu du rendu SMS (mobile de l'étudiant) :
                </span>
                <p className="text-xs text-foreground font-mono bg-background p-2.5 rounded-lg border border-border/80">
                  {previewSms}
                </p>
              </div>
            </TabsContent>
          </Tabs>

          <div className="flex justify-end gap-3 pt-3 border-t">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} className="rounded-xl">
              Fermer
            </Button>
            <Button type="button" onClick={handleSaveAll} className="rounded-xl shadow-sm">
              <Save className="h-4 w-4 mr-2" /> Enregistrer Tous les Modèles
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
