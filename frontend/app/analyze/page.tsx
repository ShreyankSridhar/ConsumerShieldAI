"use client";

import { useRef, useState } from "react";
import { Clipboard, FileText, Images, Loader2, ScanText, ShieldAlert, Upload } from "lucide-react";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { getApiBaseUrl } from "@/lib/utils";

type EvidenceSource = { title: string; source_type: string; content: string; relevance_score: number };
type Recommendation = { action: string; reason: string; evidence: string; confidence?: number };
type ScoreComponent = {
  name: string;
  score: number;
  weight: number;
  contribution: number;
  explanation: string;
};
type CaseStrengthExplanation = {
  components: ScoreComponent[];
  strong_contributors: string[];
  weak_factors: string[];
  missing_evidence: string[];
};
type TimelineAnalysis = {
  purchase_date?: string | null;
  current_date: string;
  return_window_days: number;
  warranty_window_days: number;
  days_since_purchase?: number | null;
  return_window_status: string;
  warranty_window_status: string;
  findings: string[];
};
type InvestigationFacts = {
  retailer: string;
  product_name: string;
  brand: string;
  order_id: string;
  invoice_number: string;
  resolution_requested: string;
  issue_category: string;
  seller_name: string;
  evidence: string[];
  product: string;
  order_date: string;
  delivery_date: string;
  complaint_date: string;
  purchase_price: string;
  seller: string;
  requested_resolution: string;
  evidence_available: string[];
};
type EvidenceAssessmentItem = {
  evidence_type: string;
  checks: string[];
  missing: string[];
  score: number;
};
type PolicyMatchAnalysis = {
  retailer_policy: string;
  return_window_status: string;
  warranty_status: string;
  retailer_response_consistency: string;
  notes: string[];
};
type AnalysisResult = {
  retailer?: string;
  needs_clarification?: boolean;
  clarification_question?: string;
  case_category: string;
  rights_summary: string;
  reasons: string[];
  evidence_sources: EvidenceSource[];
  evidence_completeness_score: number;
  consumer_case_strength_score: number;
  case_verdict: string;
  timeline_analysis: TimelineAnalysis;
  case_strength_score: number;
  case_strength_label: string;
  case_strength_explanation: CaseStrengthExplanation;
  confidence_score?: number;
  analysis_confidence_score: number;
  investigation_facts: InvestigationFacts;
  evidence_assessment: EvidenceAssessmentItem[];
  positive_factors: string[];
  negative_factors: string[];
  policy_match_analysis: PolicyMatchAnalysis;
  recommended_actions: Recommendation[];
  recommended_next_action: string;
  email_draft: string;
  complaint_letter: string;
  extracted_text?: string;
  disclaimer: string;
};

export default function AnalyzePage() {
  const [complaint, setComplaint] = useState("");
  const [invoice, setInvoice] = useState<File | null>(null);
  const [screenshot, setScreenshot] = useState<File | null>(null);
  const [productImage, setProductImage] = useState<File | null>(null);
  const [extractedText, setExtractedText] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [error, setError] = useState("");
  const complaintRef = useRef<HTMLTextAreaElement>(null);
  const extractedTextRef = useRef<HTMLTextAreaElement>(null);

  function getCombinedText() {
    const liveComplaint = complaintRef.current?.value ?? complaint;
    const liveExtractedText = extractedTextRef.current?.value ?? extractedText;
    return [liveComplaint, liveExtractedText].map((text) => text.trim()).filter(Boolean).join("\n\nOCR text:\n");
  }

  async function analyzeCase() {
    const combinedText = getCombinedText();
    if (!combinedText) {
      setError("Enter complaint details or extracted OCR text before analysis.");
      return;
    }

    setLoadingAnalysis(true);
    setError("");
    setResult(null);
    const formData = new FormData();
    formData.append("complaint_text", combinedText);
    if (invoice) formData.append("invoice", invoice);
    if (screenshot) formData.append("screenshot", screenshot);
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/analyze`, { method: "POST", body: formData });
      if (!response.ok) throw new Error("Analysis failed. Check that the FastAPI server is running.");
      const data = await response.json();
      setResult(data);
      if (data.extracted_text) setExtractedText(data.extracted_text);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoadingAnalysis(false);
    }
  }

  async function copyText(text: string) {
    await navigator.clipboard.writeText(text);
  }

  function displayScore(primary: number | undefined, fallback: number) {
    return typeof primary === "number" ? primary : fallback;
  }

  function formatDate(value?: string | null, fallback = "Not Detected") {
    if (!value) return fallback;
    const date = new Date(`${value}T00:00:00`);
    if (Number.isNaN(date.getTime())) return fallback;
    return date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
  }

  function returnWindowSummary(timeline?: TimelineAnalysis) {
    const daysSince = timeline?.days_since_purchase;
    const windowDays = timeline?.return_window_days ?? 7;
    if (typeof daysSince !== "number") {
      return { status: "Purchase Date Required", detail: `${windowDays} Day Return Window` };
    }
    const remaining = windowDays - daysSince;
    if (remaining >= 0) {
      return { status: "🟢 Within Return Window", detail: `${remaining} ${remaining === 1 ? "Day" : "Days"} Remaining` };
    }
    const expiredDays = Math.abs(remaining);
    return { status: "🔴 Return Window Expired", detail: `Expired ${expiredDays} ${expiredDays === 1 ? "Day" : "Days"} Ago` };
  }

  function warrantyWindowSummary(timeline?: TimelineAnalysis) {
    const daysSince = timeline?.days_since_purchase;
    const warrantyDays = timeline?.warranty_window_days ?? 365;
    if (warrantyDays <= 0) {
      return { status: "No Manufacturer Warranty", detail: "Not Applicable" };
    }
    if (typeof daysSince !== "number") {
      return { status: "Purchase Date Required", detail: `${warrantyDays} Day Warranty Window` };
    }
    const remaining = warrantyDays - daysSince;
    if (remaining >= 0) {
      return { status: "🟢 Active", detail: `${remaining} ${remaining === 1 ? "Day" : "Days"} Remaining` };
    }
    return { status: "🔴 Warranty Expired", detail: "Expired" };
  }

  function confidenceLabel(score: number) {
    if (score >= 85) return "High";
    if (score >= 60) return "Moderate";
    return "Low";
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <a href="/" className="text-lg font-bold text-slate-950">ConsumerSheildAI</a>
          <span className="rounded-md bg-indigo-50 px-3 py-2 text-xs font-semibold text-indigo-700">Explainable Consumer Navigator</span>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[0.9fr_1.1fr] lg:px-8">
        <section className="space-y-5">
          <Card>
            <CardHeader>
              <CardTitle>Complaint Analysis</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <label className="block text-sm font-semibold text-slate-700" htmlFor="complaint">Complaint Text Area</label>
              <textarea
                id="complaint"
                ref={complaintRef}
                value={complaint}
                onChange={(event) => setComplaint(event.target.value)}
                onInput={(event) => setComplaint(event.currentTarget.value)}
                className="min-h-44 w-full resize-y rounded-md border border-slate-300 bg-white p-3 text-sm outline-none ring-indigo-600 focus:ring-2"
                placeholder="Describe the product, platform, dates, seller response, refund or warranty issue, and what outcome you want."
              />

              <div className="grid gap-3 sm:grid-cols-3">
                <label className="flex cursor-pointer flex-col gap-2 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-sm">
                  <FileText className="h-5 w-5 text-indigo-600" />
                  <span className="font-semibold">Invoice Upload</span>
                  <span className="truncate text-slate-500">{invoice?.name ?? "PDF or image invoice"}</span>
                  <input className="sr-only" type="file" accept=".pdf,image/*" onChange={(event) => setInvoice(event.target.files?.[0] ?? null)} />
                </label>
                <label className="flex cursor-pointer flex-col gap-2 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-sm">
                  <Upload className="h-5 w-5 text-indigo-600" />
                  <span className="font-semibold">Screenshot Upload</span>
                  <span className="truncate text-slate-500">{screenshot?.name ?? "Chat, order, or policy screenshot"}</span>
                  <input
                    className="sr-only"
                    type="file"
                    accept="image/*"
                    onChange={(event) => {
                      const file = event.target.files?.[0] ?? null;
                      setScreenshot(file);
                    }}
                  />
                </label>
                <label
                  className="flex cursor-pointer flex-col gap-2 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-sm"
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={(event) => {
                    event.preventDefault();
                    const file = event.dataTransfer.files?.[0] ?? null;
                    if (file) setProductImage(file);
                  }}
                >
                  <Images className="h-5 w-5 text-indigo-600" />
                  <span className="font-semibold">Product Image</span>
                  <span className="truncate text-slate-500">{productImage?.name ?? "Damage, wrong item, packaging..."}</span>
                  <input
                    className="sr-only"
                    type="file"
                    accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
                    onChange={(event) => setProductImage(event.target.files?.[0] ?? null)}
                  />
                </label>
              </div>

              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="mb-3 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm font-semibold"><ScanText className="h-4 w-4 text-indigo-600" /> Extracted OCR Text</div>
                </div>
                <textarea
                  ref={extractedTextRef}
                  value={extractedText}
                  onChange={(event) => setExtractedText(event.target.value)}
                  onInput={(event) => setExtractedText(event.currentTarget.value)}
                  className="min-h-28 w-full resize-y rounded-md border border-slate-300 p-3 text-sm outline-none ring-indigo-600 focus:ring-2"
                  placeholder="Screenshot text appears here and can be edited before analysis."
                />
              </div>

              {error && <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm font-medium text-red-700">{error}</p>}
              <Button className="w-full" size="lg" onClick={analyzeCase} disabled={loadingAnalysis}>
                {loadingAnalysis ? <Loader2 className="h-5 w-5 animate-spin" /> : null}
                Analyze Case
              </Button>
              <p className="flex gap-2 rounded-md bg-slate-100 p-3 text-xs leading-5 text-slate-600">
                <ShieldAlert className="h-4 w-4 shrink-0 text-indigo-600" />
                This platform provides informational guidance and does not constitute legal advice.
              </p>
            </CardContent>
          </Card>
        </section>

        <section className="space-y-5">
          {!result ? (
            <Card className="min-h-[520px]">
              <CardHeader>
                <CardTitle>Output Dashboard</CardTitle>
              </CardHeader>
              <CardContent className="grid min-h-[420px] place-items-center text-center text-slate-500">
                <div>
                  <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-md bg-indigo-50 text-indigo-600">
                    <Clipboard className="h-6 w-6" />
                  </div>
                  <p className="font-semibold text-slate-700">Your evidence-backed guidance will appear here.</p>
                  <p className="mt-2 text-sm">The dashboard includes category, explanations, sources, case strength, actions, and complaint drafts.</p>
                </div>
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="grid gap-4 md:grid-cols-4">
                <Card>
                  <CardHeader><CardTitle>Case Category</CardTitle></CardHeader>
                  <CardContent className="text-2xl font-bold text-indigo-700">{result.case_category}</CardContent>
                </Card>
                <Card>
                  <CardHeader><CardTitle>Retailer</CardTitle></CardHeader>
                  <CardContent className="text-2xl font-bold capitalize text-indigo-700">{result.retailer ?? "Needed"}</CardContent>
                </Card>
                <Card>
                  <CardHeader><CardTitle>Case Strength Score</CardTitle></CardHeader>
                  <CardContent>
                    {(() => {
                      const score = displayScore(result.consumer_case_strength_score, result.case_strength_score);
                      const label = result.case_verdict ?? result.case_strength_label;
                      return (
                        <>
                          <div className="mb-2 flex items-center justify-between text-sm font-semibold">
                            <span>{label}</span><span>{score}%</span>
                          </div>
                          <Progress value={score} />
                          <span className="mt-3 inline-flex rounded-md bg-indigo-50 px-2 py-1 text-xs font-bold text-indigo-700">
                            {label}
                          </span>
                        </>
                      );
                    })()}
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader><CardTitle>Evidence Completeness</CardTitle></CardHeader>
                  <CardContent>
                    <div className="mb-2 flex items-center justify-between text-sm font-semibold">
                      <span>Evidence Available</span><span>{result.evidence_completeness_score ?? 0}%</span>
                    </div>
                    <Progress value={result.evidence_completeness_score ?? 0} />
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader><CardTitle>Investigation Summary</CardTitle></CardHeader>
                <CardContent>
                  {(() => {
                    const confidence = result.analysis_confidence_score ?? result.confidence_score ?? 0;
                    const returnWindow = returnWindowSummary(result.timeline_analysis);
                    const warrantyWindow = warrantyWindowSummary(result.timeline_analysis);
                    const summaryCards = [
                      { label: "Purchase Date", value: formatDate(result.timeline_analysis?.purchase_date), detail: "" },
                      { label: "Current Date", value: formatDate(result.timeline_analysis?.current_date, formatDate(new Date().toISOString().slice(0, 10))), detail: "" },
                      { label: "Return Window", value: returnWindow.status, detail: returnWindow.detail },
                      { label: "Warranty Window", value: warrantyWindow.status, detail: warrantyWindow.detail },
                      { label: "Analysis Confidence", value: `${confidence}%`, detail: confidenceLabel(confidence) },
                    ];
                    return (
                      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                        {summaryCards.map((card) => (
                          <div
                            key={card.label}
                            className={card.label === "Analysis Confidence"
                              ? "rounded-md border border-indigo-200 bg-indigo-50 p-4 shadow-sm ring-1 ring-indigo-100"
                              : "rounded-md border border-slate-200 bg-slate-50 p-4"}
                          >
                            <p className={card.label === "Analysis Confidence" ? "text-xs font-bold uppercase text-indigo-700" : "text-xs font-semibold uppercase text-slate-500"}>{card.label}</p>
                            <p className={card.label === "Analysis Confidence" ? "mt-2 text-3xl font-extrabold text-indigo-950" : "mt-2 text-lg font-bold text-slate-900"}>{card.value}</p>
                            {card.label === "Analysis Confidence" ? <Progress value={confidence} className="mt-3" /> : null}
                            {card.detail ? <p className={card.label === "Analysis Confidence" ? "mt-2 text-sm font-bold text-indigo-800" : "mt-1 text-sm font-semibold text-slate-600"}>{card.detail}</p> : null}
                          </div>
                        ))}
                      </div>
                    );
                  })()}
                </CardContent>
              </Card>

              {result.evidence_assessment?.length ? (
                <Card>
                  <CardHeader><CardTitle>Invoice Evidence Assessment</CardTitle></CardHeader>
                  <CardContent className="grid gap-3 md:grid-cols-2">
                    {result.evidence_assessment.map((item) => (
                      <div key={item.evidence_type} className="rounded-md border border-slate-200 bg-white p-4">
                        <div className="mb-3 flex items-center justify-between gap-3">
                          <p className="font-semibold text-slate-800">{item.evidence_type}</p>
                          <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700">{item.score}%</span>
                        </div>
                        <Progress value={item.score} />
                        {item.checks.length ? (
                          <ul className="mt-3 space-y-1 text-sm text-emerald-800">
                            {item.checks.map((check) => <li key={check}>✓ {check}</li>)}
                          </ul>
                        ) : null}
                        {item.evidence_type !== "Invoice" && item.missing.length ? (
                          <ul className="mt-3 space-y-1 text-sm text-rose-800">
                            {item.missing.map((missing) => <li key={missing}>- {missing}</li>)}
                          </ul>
                        ) : null}
                      </div>
                    ))}
                  </CardContent>
                </Card>
              ) : null}

              {result.needs_clarification ? (
                <Card className="border-indigo-200 bg-indigo-50">
                  <CardHeader><CardTitle>Platform Needed</CardTitle></CardHeader>
                  <CardContent className="leading-7 text-slate-700">
                    {result.clarification_question}
                  </CardContent>
                </Card>
              ) : null}

              <Card>
                <CardHeader><CardTitle>Rights Summary</CardTitle></CardHeader>
                <CardContent className="leading-7 text-slate-700">{result.rights_summary}</CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle>Explainable AI Panel</CardTitle></CardHeader>
                <CardContent>
                  <div className="grid gap-3 sm:grid-cols-3">
                    {result.reasons.map((reason) => (
                      <div key={reason} className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm font-medium text-slate-700">{reason}</div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle>Why This Verdict?</CardTitle></CardHeader>
                <CardContent>
                  <Accordion type="single" collapsible>
                    <AccordionItem value="score-breakdown">
                      <AccordionTrigger>
                        Case Strength Score: {displayScore(result.consumer_case_strength_score, result.case_strength_score)}% · {result.case_verdict ?? result.case_strength_label}
                      </AccordionTrigger>
                      <AccordionContent>
                        <div className="grid gap-4 md:grid-cols-2">
                          <div>
                            <p className="mb-2 font-semibold text-slate-800">Strong Factors</p>
                            <ul className="space-y-2">
                              {result.case_strength_explanation.strong_contributors.map((item) => (
                                <li key={item} className="rounded-md bg-emerald-50 p-2 text-sm text-emerald-800">{item}</li>
                              ))}
                            </ul>
                          </div>
                          <div>
                            <p className="mb-2 font-semibold text-slate-800">Weak Factors</p>
                            <ul className="space-y-2">
                              {(result.case_strength_explanation.weak_factors ?? []).map((item) => (
                                <li key={item} className="rounded-md bg-rose-50 p-2 text-sm text-rose-800">{item}</li>
                              ))}
                            </ul>
                          </div>
                        </div>
                        <div className="mt-4">
                          <p className="mb-2 font-semibold text-slate-800">Missing Evidence</p>
                          <ul className="grid gap-2 md:grid-cols-2">
                            {result.case_strength_explanation.missing_evidence.map((item) => (
                              <li key={item} className="rounded-md bg-amber-50 p-2 text-sm text-amber-900">{item}</li>
                            ))}
                          </ul>
                        </div>
                        <div className="mt-4 space-y-2">
                          {result.case_strength_explanation.components.map((component) => (
                            <div key={component.name} className="rounded-md border border-slate-200 bg-white p-3">
                              <div className="flex flex-wrap items-center justify-between gap-2 text-sm font-semibold">
                                <span>{component.name}</span>
                                <span>{Math.round(component.contribution)}%</span>
                              </div>
                              <p className="mt-1 text-sm text-slate-600">{component.explanation}</p>
                            </div>
                          ))}
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  </Accordion>
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle>Positive and Negative Factors</CardTitle></CardHeader>
                <CardContent className="grid gap-4 md:grid-cols-2">
                  <div>
                    <p className="mb-2 font-semibold text-slate-800">Positive Factors</p>
                    <ul className="space-y-2">
                      {(result.positive_factors ?? []).length ? result.positive_factors.map((item) => (
                        <li key={item} className="rounded-md bg-emerald-50 p-2 text-sm text-emerald-800">+ {item}</li>
                      )) : <li className="rounded-md bg-slate-100 p-2 text-sm text-slate-600">No strong positive factor found yet.</li>}
                    </ul>
                  </div>
                  <div>
                    <p className="mb-2 font-semibold text-slate-800">Negative Factors / Seller Defenses</p>
                    <ul className="space-y-2">
                      {(result.negative_factors ?? []).length ? result.negative_factors.map((item) => (
                        <li key={item} className="rounded-md bg-rose-50 p-2 text-sm text-rose-800">- {item}</li>
                      )) : <li className="rounded-md bg-slate-100 p-2 text-sm text-slate-600">No major negative factor detected.</li>}
                    </ul>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle>Policy Matching</CardTitle></CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid gap-3 sm:grid-cols-3">
                    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                      <p className="text-xs font-semibold uppercase text-slate-500">Retailer Policy</p>
                      <p className="mt-1 font-bold text-slate-800">{result.policy_match_analysis?.retailer_policy ?? "Unknown"}</p>
                    </div>
                    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                      <p className="text-xs font-semibold uppercase text-slate-500">Return Window</p>
                      <p className="mt-1 font-bold capitalize text-slate-800">{result.policy_match_analysis?.return_window_status ?? "unknown"}</p>
                    </div>
                    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                      <p className="text-xs font-semibold uppercase text-slate-500">Warranty</p>
                      <p className="mt-1 font-bold capitalize text-slate-800">{result.policy_match_analysis?.warranty_status ?? "unknown"}</p>
                    </div>
                  </div>
                  <p className="rounded-md bg-slate-100 p-3 text-sm text-slate-700">
                    {result.policy_match_analysis?.retailer_response_consistency ?? "Policy consistency could not be determined from the available information."}
                  </p>
                  {result.policy_match_analysis?.notes?.length ? (
                    <ul className="space-y-2">
                      {result.policy_match_analysis.notes.map((note) => (
                        <li key={note} className="rounded-md bg-indigo-50 p-2 text-sm text-indigo-800">{note}</li>
                      ))}
                    </ul>
                  ) : null}
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle>Evidence Sources</CardTitle></CardHeader>
                <CardContent>
                  <Accordion type="single" collapsible>
                    {result.evidence_sources.map((source, index) => (
                      <AccordionItem value={`source-${index}`} key={`${source.title}-${index}`}>
                        <AccordionTrigger>{source.title} · {Math.round(source.relevance_score * 100)}% match</AccordionTrigger>
                        <AccordionContent>{source.content}</AccordionContent>
                      </AccordionItem>
                    ))}
                  </Accordion>
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle>Recommended Next Action</CardTitle></CardHeader>
                <CardContent className="leading-7 text-slate-700">
                  {result.recommended_next_action || "Review the available facts and add missing evidence before taking action."}
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle>Recommended Actions</CardTitle></CardHeader>
                <CardContent className="space-y-4">
                  {result.recommended_actions.map((action, index) => (
                    <div key={action.action} className="grid grid-cols-[2rem_1fr] gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-sm font-bold text-white">{index + 1}</div>
                      <div className="rounded-md border border-slate-200 bg-white p-4">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="font-semibold">{action.action}</p>
                        </div>
                        <p className="mt-2 text-sm text-slate-600"><strong>Reason:</strong> {action.reason}</p>
                        <p className="mt-1 text-sm text-slate-600"><strong>Evidence:</strong> {action.evidence}</p>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>

              {[
                  ["Email Draft", result.email_draft],
                  ["Complaint Letter", result.complaint_letter],
                ].some(([, body]) => Boolean(body)) ? (
                <div className="grid gap-4 md:grid-cols-2">
                  {[
                    ["Email Draft", result.email_draft],
                    ["Complaint Letter", result.complaint_letter],
                  ].filter(([, body]) => Boolean(body)).map(([title, body]) => (
                  <Card key={title}>
                    <CardHeader className="flex flex-row items-center justify-between">
                      <CardTitle>{title}</CardTitle>
                      <Button variant="outline" size="icon" title={`Copy ${title}`} onClick={() => copyText(body)}>
                        <Clipboard className="h-4 w-4" />
                      </Button>
                    </CardHeader>
                    <CardContent>
                      <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-md bg-slate-50 p-3 text-sm leading-6 text-slate-700">{body}</pre>
                    </CardContent>
                  </Card>
                  ))}
                </div>
              ) : null}
            </>
          )}
        </section>
      </div>
    </main>
  );
}
