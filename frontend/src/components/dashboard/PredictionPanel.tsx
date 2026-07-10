import { motion, AnimatePresence } from "framer-motion";
import { ShieldCheck, ShieldAlert, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/Card";
import { Badge } from "../ui/Badge";
import type { Prediction } from "../../types";
import { issueLabel } from "../../lib/utils";

export function PredictionPanel({ prediction }: { prediction: Prediction | null }) {
  const isAnomaly = prediction?.is_anomaly ?? false;

  return (
    <Card className="relative overflow-hidden">
      {isAnomaly && (
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-crit/5 to-transparent" />
      )}
      <CardHeader>
        <CardTitle>ML Prediction</CardTitle>
        {prediction && (
          <span className="font-mono text-[11px] text-dim">
            {prediction.model_name} · {(prediction.confidence * 100).toFixed(0)}% confidence
          </span>
        )}
      </CardHeader>
      <CardContent>
        <AnimatePresence mode="wait">
          <motion.div
            key={prediction ? `${prediction.id}` : "empty"}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
          >
            {!prediction ? (
              <p className="text-sm text-dim">Waiting for the first reading...</p>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  {isAnomaly ? (
                    <ShieldAlert size={28} className="text-crit shrink-0" />
                  ) : (
                    <ShieldCheck size={28} className="text-good shrink-0" />
                  )}
                  <div>
                    <div className="font-display text-lg font-semibold">
                      {issueLabel[prediction.predicted_issue] ?? prediction.predicted_issue}
                    </div>
                    <Badge variant={isAnomaly ? "crit" : "good"} className="mt-0.5">
                      {isAnomaly ? "Anomaly detected" : "Nominal"}
                    </Badge>
                  </div>
                </div>

                <p className="text-sm leading-relaxed text-mute">{prediction.recommendation}</p>

                {Object.keys(prediction.explanation).length > 0 && (
                  <div>
                    <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-dim uppercase tracking-wide">
                      <Sparkles size={12} />
                      Top contributing signals
                    </div>
                    <div className="space-y-1.5">
                      {Object.entries(prediction.explanation)
                        .filter(([k]) => !k.startsWith("_"))
                        .slice(0, 4)
                        .map(([feature, weight]) => (
                          <div key={feature} className="flex items-center gap-2 text-xs">
                            <span className="w-40 truncate font-mono text-dim">{feature}</span>
                            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-hairline">
                              <div
                                className="h-full rounded-full bg-signal"
                                style={{ width: `${Math.min(100, weight * 100)}%` }}
                              />
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </CardContent>
    </Card>
  );
}
