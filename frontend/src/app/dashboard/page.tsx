"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type UserResponse } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FileText, Bot, Search, DollarSign } from "lucide-react";

export default function DashboardPage() {
  const [user, setUser] = useState<UserResponse | null>(null);

  useEffect(() => {
    api.me().then(setUser).catch(() => {});
  }, []);

  const cards = [
    { title: "Documents", desc: "Upload & manage knowledge base", icon: FileText, href: "/dashboard/documents" },
    { title: "Knowledge Query", desc: "RAG-powered Q&A", icon: Search, href: "/dashboard/knowledge" },
    { title: "AI Agent", desc: "LangGraph agent with tools", icon: Bot, href: "/dashboard/agent" },
    { title: "LLMOps", desc: "Token tracking & cost monitoring", icon: DollarSign, href: "/dashboard/llm" },
  ];

  return (
    <div>
      <h1 className="mb-2 text-2xl font-bold text-white">
        Welcome{user ? `, ${user.full_name}` : ""}
      </h1>
      <p className="mb-8 text-slate-400">
        Praello AI Knowledge Assistant for Businesses — Role: {user?.role || "loading..."}
      </p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <Link key={card.title} href={card.href}>
              <Card className="hover:border-blue-600/50 transition-colors">
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Icon className="h-5 w-5 text-blue-500" />
                    <CardTitle>{card.title}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-slate-400">{card.desc}</p>
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
