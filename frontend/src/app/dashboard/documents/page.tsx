"use client";

import { useEffect, useState } from "react";
import { api, type DocumentResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Upload } from "lucide-react";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const load = () => api.listDocuments().then((r) => setDocuments(r.items)).catch(() => {});

  useEffect(() => { load(); }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      await api.uploadDocument(file);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const statusVariant = (s: string) =>
    s === "indexed" ? "success" : s === "failed" ? "error" : "warning";

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Documents</h1>
          <p className="text-slate-400">Upload PDF, DOCX, or Markdown files</p>
        </div>
        <label className="cursor-pointer">
          <input
            type="file"
            className="hidden"
            accept=".pdf,.docx,.md,.txt,.markdown"
            onChange={handleUpload}
          />
          <span className="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500">
            <Upload className="mr-2 h-4 w-4" />
            {uploading ? "Uploading..." : "Upload"}
          </span>
        </label>
      </div>
      {error && <p className="mb-4 text-red-400">{error}</p>}
      <div className="space-y-3">
        {documents.length === 0 && (
          <p className="text-slate-500">No documents yet. Upload your first file.</p>
        )}
        {documents.map((doc) => (
          <Card key={doc.id}>
            <CardHeader className="flex-row items-center justify-between py-4">
              <CardTitle className="text-base">{doc.original_filename}</CardTitle>
              <Badge variant={statusVariant(doc.status)}>{doc.status}</Badge>
            </CardHeader>
            <CardContent className="text-sm text-slate-400">
              {doc.document_type} · {doc.chunk_count} chunks
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
