import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Upload, FileText, Check } from "lucide-react";
import { toast } from "sonner";

const PreInscription = () => {
  const [step, setStep] = useState(1);
  const [files, setFiles] = useState<{ [key: string]: File | null }>({
    photo: null,
    diplome: null,
    cv: null,
    lettreMotivation: null,
  });

  const handleFileChange = (key: string, file: File | null) => {
    setFiles((prev) => ({ ...prev, [key]: file }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    toast.success("Pré-inscription soumise avec succès !");
    setStep(3);
  };

  if (step === 3) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="w-full max-w-md text-center">
          <CardContent className="pt-12 pb-8">
            <div className="mx-auto w-16 h-16 rounded-full bg-success/10 flex items-center justify-center mb-6">
              <Check className="h-8 w-8 text-success" />
            </div>
            <h2 className="text-2xl font-bold text-foreground mb-2">
              Inscription Enregistrée !
            </h2>
            <p className="text-muted-foreground mb-6">
              Votre dossier de pré-inscription a été soumis avec succès. Vous recevrez
              une confirmation par email dans les prochaines heures.
            </p>
            <Button onClick={() => setStep(1)} className="w-full">
              Nouvelle Inscription
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Pré-inscription en Ligne</h1>
        <p className="text-muted-foreground mt-2">
          Remplissez le formulaire pour soumettre votre candidature
        </p>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center justify-between mb-8">
        {[
          { num: 1, label: "Informations" },
          { num: 2, label: "Documents" },
        ].map((s) => (
          <div key={s.num} className="flex items-center flex-1">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-colors ${
                step >= s.num
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {s.num}
            </div>
            <span
              className={`ml-3 font-medium ${
                step >= s.num ? "text-foreground" : "text-muted-foreground"
              }`}
            >
              {s.label}
            </span>
            {s.num < 2 && (
              <div
                className={`flex-1 h-1 mx-4 rounded ${
                  step > s.num ? "bg-primary" : "bg-muted"
                }`}
              />
            )}
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit}>
        {step === 1 && (
          <Card>
            <CardHeader>
              <CardTitle>Informations Personnelles</CardTitle>
              <CardDescription>
                Veuillez renseigner vos informations personnelles
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="nom">Nom *</Label>
                  <Input id="nom" placeholder="Votre nom" required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="prenom">Prénom *</Label>
                  <Input id="prenom" placeholder="Votre prénom" required />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="email">Email *</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="votre.email@exemple.com"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="telephone">Téléphone *</Label>
                  <Input
                    id="telephone"
                    type="tel"
                    placeholder="+225 XX XX XX XX XX"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="dateNaissance">Date de Naissance *</Label>
                  <Input id="dateNaissance" type="date" required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="nationalite">Nationalité *</Label>
                  <Input id="nationalite" placeholder="Ivoirienne" required />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="adresse">Adresse Complète *</Label>
                <Textarea
                  id="adresse"
                  placeholder="Votre adresse complète"
                  required
                  rows={3}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="filiere">Filière Souhaitée *</Label>
                  <Select required>
                    <SelectTrigger>
                      <SelectValue placeholder="Sélectionner une filière" />
                    </SelectTrigger>
                    <SelectContent className="bg-popover">
                      <SelectItem value="info">Informatique</SelectItem>
                      <SelectItem value="gestion">Gestion</SelectItem>
                      <SelectItem value="commerce">Commerce</SelectItem>
                      <SelectItem value="droit">Droit</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="niveau">Niveau d'Études *</Label>
                  <Select required>
                    <SelectTrigger>
                      <SelectValue placeholder="Sélectionner un niveau" />
                    </SelectTrigger>
                    <SelectContent className="bg-popover">
                      <SelectItem value="licence1">Licence 1</SelectItem>
                      <SelectItem value="licence2">Licence 2</SelectItem>
                      <SelectItem value="licence3">Licence 3</SelectItem>
                      <SelectItem value="master1">Master 1</SelectItem>
                      <SelectItem value="master2">Master 2</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex justify-end pt-6">
                <Button type="button" onClick={() => setStep(2)} size="lg">
                  Suivant
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {step === 2 && (
          <Card>
            <CardHeader>
              <CardTitle>Documents Requis</CardTitle>
              <CardDescription>
                Veuillez télécharger les documents nécessaires à votre inscription
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {[
                { key: "photo", label: "Photo d'Identité", required: true },
                { key: "diplome", label: "Copie du Diplôme", required: true },
                { key: "cv", label: "Curriculum Vitae", required: false },
                { key: "lettreMotivation", label: "Lettre de Motivation", required: false },
              ].map((doc) => (
                <div key={doc.key} className="space-y-2">
                  <Label htmlFor={doc.key}>
                    {doc.label} {doc.required && "*"}
                  </Label>
                  <div className="flex items-center gap-4">
                    <div className="flex-1 relative">
                      <Input
                        id={doc.key}
                        type="file"
                        className="cursor-pointer"
                        onChange={(e) =>
                          handleFileChange(
                            doc.key,
                            e.target.files ? e.target.files[0] : null
                          )
                        }
                        required={doc.required}
                      />
                    </div>
                    {files[doc.key] && (
                      <div className="flex items-center gap-2 text-success text-sm">
                        <FileText className="h-4 w-4" />
                        <span>{files[doc.key]?.name}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              <div className="bg-accent rounded-lg p-4 mt-6">
                <p className="text-sm text-accent-foreground">
                  <strong>Note :</strong> Les documents doivent être au format PDF, JPG
                  ou PNG et ne pas dépasser 5 Mo chacun.
                </p>
              </div>

              <div className="flex justify-between pt-6">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setStep(1)}
                  size="lg"
                >
                  Précédent
                </Button>
                <Button type="submit" size="lg">
                  Soumettre la Candidature
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </form>
    </div>
  );
};

export default PreInscription;
