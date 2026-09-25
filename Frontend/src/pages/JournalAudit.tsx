import { useCallback, useEffect, useState } from "react";
import { AlertCircle, Loader2, RefreshCw, ShieldCheck } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { auditApi, extractErrorMessage } from "@/services/apiClient";
import type { AuditEvent } from "@/services/apiTypes";

const JournalAudit = () => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [actionFilter, setActionFilter] = useState("");
  const [resourceTypeFilter, setResourceTypeFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadEvents = useCallback(async () => {
    setLoading(true);
    setError(null);
    const result = await auditApi.getEvents({
      action: actionFilter.trim() || undefined,
      resourceType: resourceTypeFilter.trim() || undefined,
      limit: 200,
    });
    if (result.error) {
      setError(extractErrorMessage(result.error, "Le journal d'audit est indisponible."));
      setEvents([]);
    } else {
      setEvents(result.data || []);
    }
    setLoading(false);
  }, [actionFilter, resourceTypeFilter]);

  useEffect(() => {
    void loadEvents();
  }, [loadEvents]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Journal d'audit</h1>
          <p className="mt-1 text-muted-foreground">Traçabilité serveur des actions sensibles de sécurité.</p>
        </div>
        <Button variant="outline" onClick={() => void loadEvents()} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Actualiser
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Erreur backend</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-primary" />
            Événements de sécurité
          </CardTitle>
          <CardDescription>
            Cette vue charge au maximum 200 événements, du plus récent au plus ancien.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2">
            <Input
              value={actionFilter}
              onChange={(event) => setActionFilter(event.target.value)}
              placeholder="Filtrer par action, ex. security.user.updated"
              aria-label="Filtrer par action"
            />
            <Input
              value={resourceTypeFilter}
              onChange={(event) => setResourceTypeFilter(event.target.value)}
              placeholder="Filtrer par ressource, ex. user"
              aria-label="Filtrer par ressource"
            />
          </div>

          <div className="overflow-x-auto rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50">
                  <TableHead>Date</TableHead>
                  <TableHead>Acteur</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Ressource</TableHead>
                  <TableHead>Résultat</TableHead>
                  <TableHead>Détails</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow><TableCell colSpan={6} className="py-10 text-center"><Loader2 className="mx-auto h-5 w-5 animate-spin" /></TableCell></TableRow>
                ) : events.length === 0 ? (
                  <TableRow><TableCell colSpan={6} className="py-10 text-center text-muted-foreground">Aucun événement ne correspond aux filtres.</TableCell></TableRow>
                ) : events.map((event) => (
                  <TableRow key={event.id}>
                    <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                      {new Date(event.occurred_at).toLocaleString("fr-FR")}
                    </TableCell>
                    <TableCell className="text-sm">
                      {event.actor_email || "Système"}
                      {event.actor_id ? ` (#${event.actor_id})` : ""}
                    </TableCell>
                    <TableCell><Badge variant="outline">{event.action}</Badge></TableCell>
                    <TableCell className="text-xs">
                      <span className="block font-medium">{event.resource_type}</span>
                      <span className="text-muted-foreground">{event.resource_id || "—"}</span>
                    </TableCell>
                    <TableCell>
                      <Badge variant={event.outcome === "success" ? "default" : "destructive"}>
                        {event.outcome}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-sm">
                      <details>
                        <summary className="cursor-pointer text-xs text-primary">Voir</summary>
                        <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded bg-muted p-2 text-[11px]">
                          {JSON.stringify(event.details, null, 2)}
                        </pre>
                      </details>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default JournalAudit;
