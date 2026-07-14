"use client";

import { useState } from "react";
import { api, type RAGResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function KnowledgePage() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<RAGResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleQuery = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.queryKnowledge(query);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl">
      <h1 className="mb-2 text-2xl font-bold text-white">Knowledge Query</h1>
      <p className="mb-8 text-slate-400">Hybrid RAG search with citations</p>

      <div className="space-y-4">
        <Textarea
          placeholder="Ask a question about your knowledge base..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rows={3}
        />
        <Button onClick={handleQuery} disabled={loading}>
          {loading ? "Searching..." : "Query"}
        </Button>
        {error && <p className="text-red-400">{error}</p>}
      </div>

      {result && (
        <Card className="mt-8">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Answer</CardTitle>
              <Badge variant="success">
                Confidence: {(result.confidence * 100).toFixed(0)}%
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-slate-200">{result.answer}</p>
            {result.sources.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-medium text-slate-400">Sources</h4>
                {result.sources.map((s, i) => (
                  <div key={i} className="mb-2 rounded-lg bg-slate-800/50 p-3 text-sm">
                    <p className="font-medium text-blue-400">{s.document_name}</p>
                    <p className="text-slate-400">{s.excerpt}</p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
