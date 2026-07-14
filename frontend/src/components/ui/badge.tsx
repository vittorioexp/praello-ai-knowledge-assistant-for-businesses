import { cn } from "@/lib/utils";

export function Badge({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & {
  variant?: "default" | "success" | "warning" | "error";
}) {
  const variants = {
    default: "bg-slate-800 text-slate-300",
    success: "bg-green-900/50 text-green-300",
    warning: "bg-yellow-900/50 text-yellow-300",
    error: "bg-red-900/50 text-red-300",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
