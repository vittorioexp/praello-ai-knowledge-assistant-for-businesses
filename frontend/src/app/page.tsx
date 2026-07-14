import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-slate-950 p-8">
      <div className="max-w-2xl text-center">
        <div className="mb-6 inline-flex items-center rounded-full border border-slate-700 bg-slate-900 px-4 py-1.5 text-sm text-slate-400">
          Praello AI
        </div>
        <h1 className="mb-4 text-4xl font-bold tracking-tight text-white sm:text-5xl">
          Knowledge Assistant for Businesses
        </h1>
        <p className="mb-8 text-lg text-slate-400">
          Production-ready enterprise AI with RAG, LangGraph agents,
          RBAC, and LLMOps.
        </p>
        <div className="flex flex-wrap justify-center gap-4">
          <Link href="/login">
            <Button size="lg">Sign in</Button>
          </Link>
          <Link href="/register">
            <Button variant="outline" size="lg">Create account</Button>
          </Link>
        </div>
        <div className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[
            { title: "Knowledge Base", desc: "PDF, DOCX, Markdown ingestion" },
            { title: "RAG Pipeline", desc: "Hybrid search with reranking" },
            { title: "AI Agent", desc: "LangGraph orchestration" },
          ].map((item) => (
            <div
              key={item.title}
              className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-left"
            >
              <h3 className="font-semibold text-white">{item.title}</h3>
              <p className="mt-1 text-sm text-slate-500">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
