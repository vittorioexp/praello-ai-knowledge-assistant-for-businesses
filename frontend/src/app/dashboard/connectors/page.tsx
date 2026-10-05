"use client";

import { useEffect, useState } from "react";
import { Cable, ExternalLink, RefreshCw, ShieldCheck, Trash2 } from "lucide-react";
import { api, ConnectorAccountResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const labels = { google_drive: "Google Drive", sharepoint: "SharePoint" };

export default function ConnectorsPage() {
  const [accounts, setAccounts] = useState<ConnectorAccountResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      setAccounts(await api.listConnectors());
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load connectors");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const connect = async (provider: ConnectorAccountResponse["provider"]) => {
    try {
      const { authorization_url } = await api.connectorAuthorizationUrl(provider);
      window.location.assign(authorization_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start authorization");
    }
  };

  const revoke = async (id: string) => {
    await api.revokeConnector(id);
    await load();
  };

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="mb-2 text-sm uppercase tracking-[0.2em] text-blue-400">Sources</p>
          <h1 className="text-3xl font-semibold text-white">Connected knowledge</h1>
          <p className="mt-2 max-w-xl text-slate-400">Manage the external workspaces that feed your company knowledge base.</p>
        </div>
        <Button variant="outline" onClick={() => void load()} disabled={loading}>
          <RefreshCw className="mr-2 h-4 w-4" /> Refresh
        </Button>
      </header>
      {error && <p className="border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">{error}</p>}
      <div className="grid gap-4 md:grid-cols-2">
        {(Object.keys(labels) as ConnectorAccountResponse["provider"][]).map((provider) => (
          <Card key={provider}>
            <CardHeader><CardTitle className="flex items-center gap-3"><Cable className="h-5 w-5 text-blue-400" />{labels[provider]}</CardTitle></CardHeader>
            <CardContent><Button onClick={() => void connect(provider)}><ExternalLink className="mr-2 h-4 w-4" /> Connect</Button></CardContent>
          </Card>
        ))}
      </div>
      <section className="space-y-3">
        <h2 className="text-lg font-medium text-white">Active accounts</h2>
        {loading ? <p className="text-slate-400">Loading accounts...</p> : accounts.length === 0 ? <p className="text-slate-500">No external accounts connected.</p> : accounts.map((account) => (
          <Card key={account.id} className="flex items-center justify-between p-5">
            <div><p className="font-medium text-white">{labels[account.provider]}</p><p className="text-sm text-slate-400">{account.external_account_id}</p><p className="mt-2 flex items-center gap-2 text-xs text-emerald-400"><ShieldCheck className="h-3 w-3" /> Active {account.last_sync_at ? `, last sync ${new Date(account.last_sync_at).toLocaleString()}` : ", pending first sync"}</p></div>
            <Button variant="outline" onClick={() => void revoke(account.id)} aria-label={`Revoke ${labels[account.provider]}`}><Trash2 className="h-4 w-4" /></Button>
          </Card>
        ))}
      </section>
    </div>
  );
}