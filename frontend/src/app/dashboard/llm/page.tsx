"use client";

import { useEffect, useState } from "react";
import { api, type LLMUsageResponse } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

function formatNumber(value: number): string {
  return value.toLocaleString();
}

function formatCost(value: number): string {
  return `$${value.toFixed(4)}`;
}

export default function LLMOpsPage() {
  const [usage, setUsage] = useState<LLMUsageResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .llmUsage()
      .then(setUsage)
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load usage data");
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <p className="text-slate-400">Loading usage data...</p>;
  }

  if (error) {
    return (
      <div className="max-w-2xl">
        <h1 className="mb-2 text-2xl font-bold text-white">LLMOps</h1>
        <Card>
          <CardContent className="pt-6">
            <p className="text-slate-300">
              {error.includes("knowledge:admin") || error.includes("Permission")
                ? "Admin access required. LLM usage metrics are available to admin and super_admin roles."
                : error}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!usage) return null;

  const models = Object.entries(usage.by_model);

  return (
    <div>
      <h1 className="mb-2 text-2xl font-bold text-white">LLMOps</h1>
      <p className="mb-8 text-slate-400">
        Token usage, cache hits, and estimated cost
      </p>

      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Total requests</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold text-white">
              {formatNumber(usage.total_requests)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Input tokens</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold text-white">
              {formatNumber(usage.total_input_tokens)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Output tokens</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold text-white">
              {formatNumber(usage.total_output_tokens)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Estimated cost</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold text-emerald-400">
              {formatCost(usage.total_cost_usd)}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card className="mb-8">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Cache performance</CardTitle>
            <Badge variant="default">
              {usage.cache_hits} cache hit{usage.cache_hits === 1 ? "" : "s"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-400">
            Cached responses avoid duplicate LLM calls and reduce cost.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Usage by model</CardTitle>
        </CardHeader>
        <CardContent>
          {models.length === 0 ? (
            <p className="text-sm text-slate-400">No LLM activity recorded yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400">
                    <th className="pb-3 pr-4 font-medium">Model</th>
                    <th className="pb-3 pr-4 font-medium">Requests</th>
                    <th className="pb-3 pr-4 font-medium">Input</th>
                    <th className="pb-3 pr-4 font-medium">Output</th>
                    <th className="pb-3 font-medium">Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {models.map(([model, stats]) => (
                    <tr key={model} className="border-b border-slate-800/50">
                      <td className="py-3 pr-4 text-white">{model}</td>
                      <td className="py-3 pr-4 text-slate-300">
                        {formatNumber(stats.requests)}
                      </td>
                      <td className="py-3 pr-4 text-slate-300">
                        {formatNumber(stats.input_tokens)}
                      </td>
                      <td className="py-3 pr-4 text-slate-300">
                        {formatNumber(stats.output_tokens)}
                      </td>
                      <td className="py-3 text-emerald-400">
                        {formatCost(stats.cost_usd)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
