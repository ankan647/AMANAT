import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { CheckCircle2, Search, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { MoneyText } from "@/components/amanat/MoneyText";
import { usePublicOrder, usePublicVerifyPayload } from "@/api/hooks/useOrders";
import { formatDate } from "@/lib/dates";

const SEAL_COLOR: Record<string, string> = {
  valid: "bg-emerald-500",
  revoked: "bg-rose-500",
  superseded: "bg-slate-400",
};

export function VerifyPage() {
  const { orderNo } = useParams();
  const navigate = useNavigate();
  const [input, setInput] = useState(orderNo ?? "");
  const { data, isLoading, isError } = usePublicOrder(orderNo);

  const [tamperPayload, setTamperPayload] = useState("");
  const [tamperSig, setTamperSig] = useState("");
  const verifyPayload = usePublicVerifyPayload();
  const [tamperResult, setTamperResult] = useState<boolean | null>(null);

  async function checkTamper() {
    try {
      const payload = JSON.parse(tamperPayload);
      const res = await verifyPayload.mutateAsync({ payload, signature_b64: tamperSig });
      setTamperResult(res.data.signature_valid);
    } catch {
      setTamperResult(false);
    }
  }

  if (!orderNo) {
    return (
      <Card className="w-full max-w-md">
        <CardContent className="space-y-3 p-6">
          <h1 className="text-lg font-semibold">Verify a release order</h1>
          <div className="flex gap-2">
            <Input value={input} onChange={(e) => setInput(e.target.value)} placeholder="ORD-2026-0001" />
            <Button onClick={() => navigate(`/verify/${input}`)} disabled={!input.trim()}>
              <Search className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const status = data?.data.status ?? (isError ? "not_found" : "loading");

  return (
    <div className="w-full max-w-lg space-y-6">
      <Card>
        <CardContent className="p-8 text-center">
          {isLoading && <Skeleton className="mx-auto h-24 w-24 rounded-full" />}
          {!isLoading && status !== "not_found" && (
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 200, damping: 15 }}
              className={`mx-auto flex h-24 w-24 items-center justify-center rounded-full text-white ${SEAL_COLOR[status] ?? "bg-slate-400"}`}
            >
              {status === "valid" ? <CheckCircle2 className="h-12 w-12" /> : <XCircle className="h-12 w-12" />}
            </motion.div>
          )}
          {!isLoading && status === "not_found" && (
            <div className="mx-auto flex h-24 w-24 items-center justify-center rounded-full bg-slate-300 text-white">
              <XCircle className="h-12 w-12" />
            </div>
          )}

          <h2 className="mt-4 text-xl font-semibold uppercase tracking-wide">
            {status === "valid" && "Valid"}
            {status === "revoked" && "Revoked"}
            {status === "superseded" && "Superseded"}
            {status === "not_found" && "Not found"}
          </h2>

          {data && (
            <div className="mt-4 space-y-1 text-left text-sm">
              <p><span className="text-muted-foreground">Order:</span> {data.data.order_no}</p>
              <p><span className="text-muted-foreground">Institution:</span> {data.data.institution_name}</p>
              <p><span className="text-muted-foreground">Amount:</span> <MoneyText paise={data.data.amount_paise} /></p>
              <p><span className="text-muted-foreground">Issued on:</span> {formatDate(data.data.issued_on)}</p>
              <p><span className="text-muted-foreground">Issuing authority:</span> {data.data.issuing_authority}</p>
              <p>
                <span className="text-muted-foreground">Signature:</span>{" "}
                {data.data.signature_valid ? (
                  <span className="text-emerald-600">valid</span>
                ) : (
                  <span className="text-rose-600">invalid</span>
                )}
              </p>
            </div>
          )}

          <Button variant="outline" className="mt-6" onClick={() => navigate("/verify")}>
            Verify another order
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-3 p-6">
          <h3 className="text-sm font-semibold">Tamper-test box</h3>
          <p className="text-xs text-muted-foreground">
            Paste a payload and signature; edit any field and watch verification fail.
          </p>
          <div>
            <Label>Payload (JSON)</Label>
            <Textarea value={tamperPayload} onChange={(e) => setTamperPayload(e.target.value)} className="h-28 font-mono text-xs" />
          </div>
          <div>
            <Label>Signature (base64)</Label>
            <Textarea value={tamperSig} onChange={(e) => setTamperSig(e.target.value)} className="h-16 font-mono text-xs" />
          </div>
          <Button size="sm" onClick={checkTamper}>
            Verify signature
          </Button>
          {tamperResult !== null && (
            <p className={tamperResult ? "text-sm text-emerald-600" : "text-sm text-rose-600"}>
              Signature {tamperResult ? "valid" : "invalid"}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
