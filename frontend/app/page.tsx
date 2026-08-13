import Link from "next/link";
import { ArrowRight, BadgeCheck, FileSearch, LockKeyhole, Scale, ShieldCheck, Sparkles } from "lucide-react";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const features = [
  { icon: FileSearch, title: "Evidence-first analysis", text: "Matches complaint details to policies and consumer-rights references before producing guidance." },
  { icon: Scale, title: "Rights navigation", text: "Classifies refund, product, warranty, and delivery issues into a clear escalation path." },
  { icon: ShieldCheck, title: "Responsible by design", text: "Masks personal data before storage and keeps legal-advice boundaries visible." },
];

const steps = ["Upload complaint details", "Extract invoice or screenshot text", "Retrieve relevant rights evidence", "Review actions and drafts"];

export default function LandingPage() {
  return (
    <main className="bg-white text-slate-950">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
        <nav className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-2 text-lg font-bold">
            <span className="flex h-9 w-9 items-center justify-center rounded-md bg-indigo-600 text-white"><Scale className="h-5 w-5" /></span>
            ConsumerSheildAI
          </Link>
          <div className="hidden items-center gap-6 text-sm font-medium text-slate-600 md:flex">
            <a href="#features">Features</a>
            <a href="#explainable">Explainable AI</a>
            <a href="#responsible">Responsible AI</a>
            <a href="#faq">FAQ</a>
          </div>
          <Button asChild>
            <Link href="/analyze">Analyze Complaint</Link>
          </Button>
        </nav>
      </header>

      <section className="trust-grid border-b border-slate-200">
        <div className="mx-auto grid min-h-[calc(100vh-73px)] max-w-7xl items-center gap-10 px-4 py-14 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:px-8">
          <div className="max-w-3xl">
            <div className="mb-5 inline-flex items-center gap-2 rounded-md border border-indigo-200 bg-white px-3 py-2 text-sm font-semibold text-indigo-700">
              <Sparkles className="h-4 w-4" /> Explainable consumer-rights guidance
            </div>
            <h1 className="text-4xl font-bold tracking-normal text-slate-950 sm:text-5xl lg:text-6xl">
              Understand Your Consumer Rights Instantly
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
              Upload complaints, invoices, screenshots, and receive evidence-backed guidance powered by Explainable AI.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Button asChild size="lg">
                <Link href="/analyze">Analyze Complaint <ArrowRight className="h-5 w-5" /></Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <a href="#features">Learn More</a>
              </Button>
            </div>
            <p className="mt-6 text-sm text-slate-500">
              This platform provides informational guidance and does not constitute legal advice.
            </p>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-soft">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-500">Case dashboard</p>
                <h2 className="text-2xl font-bold">Refund denial</h2>
              </div>
              <span className="rounded-md bg-indigo-50 px-3 py-2 text-sm font-bold text-indigo-700">87%</span>
            </div>
            <div className="space-y-3">
              {["Product reported defective", "Complaint within return window", "Relevant policy matched"].map((reason) => (
                <div key={reason} className="flex items-center gap-3 rounded-md border border-slate-200 p-3">
                  <BadgeCheck className="h-5 w-5 text-indigo-600" />
                  <span className="text-sm font-medium text-slate-700">{reason}</span>
                </div>
              ))}
            </div>
            <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-md bg-slate-50 p-4">
                <p className="font-semibold">Evidence</p>
                <p className="mt-1 text-slate-600">3 matched sources</p>
              </div>
              <div className="rounded-md bg-slate-50 p-4">
                <p className="font-semibold">Next step</p>
                <p className="mt-1 text-slate-600">Escalate ticket</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="max-w-2xl">
          <h2 className="text-3xl font-bold">Features</h2>
          <p className="mt-3 text-slate-600">Built for consumers who need clarity, evidence, and a practical route forward.</p>
        </div>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {features.map((feature) => (
            <Card key={feature.title}>
              <CardHeader>
                <feature.icon className="h-6 w-6 text-indigo-600" />
                <CardTitle>{feature.title}</CardTitle>
              </CardHeader>
              <CardContent className="text-sm leading-6 text-slate-600">{feature.text}</CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="border-y border-slate-200 bg-slate-50">
        <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold">How It Works</h2>
          <div className="mt-8 grid gap-4 md:grid-cols-4">
            {steps.map((step, index) => (
              <div key={step} className="rounded-lg border border-slate-200 bg-white p-5">
                <div className="mb-5 flex h-9 w-9 items-center justify-center rounded-md bg-indigo-600 text-sm font-bold text-white">{index + 1}</div>
                <p className="font-semibold text-slate-800">{step}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="explainable" className="mx-auto grid max-w-7xl gap-8 px-4 py-16 sm:px-6 lg:grid-cols-2 lg:px-8">
        <div>
          <h2 className="text-3xl font-bold">Explainable AI</h2>
          <p className="mt-4 leading-7 text-slate-600">
            ConsumerSheildAI shows the classification, reasons, evidence sources, and transparent case strength behind every answer. Recommendations are tied to retrieved references, not presented as unsupported advice.
          </p>
        </div>
        <div id="responsible">
          <h2 className="text-3xl font-bold">Responsible AI</h2>
          <p className="mt-4 leading-7 text-slate-600">
            Uploads are handled through a controlled API, the system evaluates both strong and weak case factors, and every analysis includes an informational-use disclaimer.
          </p>
        </div>
      </section>

      <section id="faq" className="border-t border-slate-200 bg-slate-50">
        <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold">FAQ</h2>
          <Accordion type="single" collapsible className="mt-6 rounded-lg border border-slate-200 bg-white px-5">
            <AccordionItem value="legal">
              <AccordionTrigger>Is this legal advice?</AccordionTrigger>
              <AccordionContent>No. ConsumerSheildAI provides informational guidance and helps organize evidence for your own follow-up.</AccordionContent>
            </AccordionItem>
            <AccordionItem value="privacy">
              <AccordionTrigger>What happens to personal data?</AccordionTrigger>
              <AccordionContent>Only share details you are comfortable using for analysis. Uploaded evidence is processed through the backend API for the case review.</AccordionContent>
            </AccordionItem>
            <AccordionItem value="sources">
              <AccordionTrigger>Which sources are used?</AccordionTrigger>
              <AccordionContent>The sample dataset includes consumer protection references and marketplace policy summaries that can be extended.</AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>
      </section>
    </main>
  );
}
