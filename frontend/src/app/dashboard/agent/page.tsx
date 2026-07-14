"use client";

import { useState } from "react";
import { api, type AgentResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Send, CheckCircle } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function AgentPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [threadId, setThreadId] = useState<string | null>(null);
  const [pending, setPending] = useState<AgentResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const send = async () => {
    if (!input.trim()) return;
    const userMsg = input;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: userMsg }]);
    setLoading(true);
    try {
      const res = await api.agentChat(userMsg, threadId || undefined);
      setThreadId(res.thread_id);
      if (res.requires_approval) {
        setPending(res);
        setMessages((m) => [
          ...m,
          { role: "assistant", content: res.answer + " (Awaiting approval)" },
        ]);
      } else {
        setMessages((m) => [...m, { role: "assistant", content: res.answer }]);
      }
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: err instanceof Error ? err.message : "Error" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const approve = async () => {
    if (!threadId || !pending) return;
    setLoading(true);
    try {
      const res = await api.approveAction(threadId, true);
      setPending(null);
      setMessages((m) => [...m, { role: "assistant", content: res.answer }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] max-w-3xl flex-col">
      <h1 className="mb-2 text-2xl font-bold text-white">AI Agent</h1>
      <p className="mb-4 text-slate-400">LangGraph agent with tool calling</p>

      <div className="flex-1 space-y-3 overflow-auto rounded-xl border border-slate-800 bg-slate-900/30 p-4">
        {messages.length === 0 && (
          <p className="text-slate-500">
            Ask about policies, query the database, or request actions.
          </p>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <Card
              className={`max-w-[80%] ${
                msg.role === "user" ? "bg-blue-600/20" : "bg-slate-800/50"
              }`}
            >
              <CardContent className="p-3 text-sm">{msg.content}</CardContent>
            </Card>
          </div>
        ))}
      </div>

      {pending && (
        <div className="my-3 flex items-center gap-3 rounded-lg border border-yellow-800 bg-yellow-900/20 p-3">
          <Badge variant="warning">Approval Required</Badge>
          <Button size="sm" onClick={approve} disabled={loading}>
            <CheckCircle className="mr-1 h-4 w-4" />
            Approve
          </Button>
        </div>
      )}

      <div className="mt-4 flex gap-2">
        <Textarea
          placeholder="Message the agent..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          rows={2}
          className="flex-1"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <Button onClick={send} disabled={loading} className="self-end">
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
