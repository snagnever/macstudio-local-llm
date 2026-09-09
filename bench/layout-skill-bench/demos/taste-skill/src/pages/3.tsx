// Marginalia. Editorial / manuscript language. Dials: V7 / M4 / D3.
// Serif justified: the brand IS marginalia, the manuscript tradition of notes in margins.
// Theme lock: warm-neutral paper (deliberate art direction for this iteration).
// Shape rule (locked): all-sharp except photo corners at 2px. Accent lock: Prussian blue.
import { memo } from "react";
import { Reveal } from "../ui";

const MOVEMENTS = [
  {
    verb: "Capture",
    indent: "md:ml-0",
    body: "A line, a quote, a doubt. Marginalia takes it the way paper does: instantly, silently, without asking where it belongs.",
  },
  {
    verb: "Chew",
    indent: "md:ml-[8vw]",
    body: "Old notes surface in the margin of new ones, the way a good book answers itself if you read it twice.",
  },
  {
    verb: "Return",
    indent: "md:ml-[4vw]",
    body: "Everything you wrote comes back at the moment it matters, annotated by everything you wrote since.",
  },
];

const KEPT = [
  {
    group: "For work",
    items: [
      "Interview notes, per candidate, per doubt",
      "The pricing page copy that never shipped",
      "Every number from the 2024 field study",
      "One-paragraph briefs for people I might hire",
      "Arguments I had with myself about the roadmap",
    ],
  },
  {
    group: "For life",
    items: [
      "The ferry timetable I can never find twice",
      "Sentences other people wrote that fixed my week",
      "Sourdough attempts, ranked honestly",
      "Dreams, written before the coffee",
      "A list of errands that turned into a memoir",
    ],
  },
];

export default memo(function Marginalia() {
  return (
    <div className="min-h-[100dvh] bg-[#FAF9F6] font-serifed text-[#20201D] antialiased">
      <header className="sticky top-0 z-40 h-16 border-b border-[#E4E1D8] bg-[#FAF9F6]/90 backdrop-blur-md">
        <div className="mx-auto flex h-full max-w-6xl items-center justify-between px-5 lg:px-8">
          <a href="#" className="text-[19px] font-semibold tracking-tight">
            Marginalia
          </a>
          <nav className="hidden items-center gap-8 font-sans text-sm text-[#5C5A52] md:flex">
            <a href="#method" className="transition-colors hover:text-[#20201D]">Method</a>
            <a href="#kept" className="transition-colors hover:text-[#20201D]">What people keep</a>
            <a href="#start" className="transition-colors hover:text-[#20201D]">Contact</a>
          </nav>
          <a
            href="#start"
            className="rounded-sm bg-[#1F3A5F] px-4 py-2 font-sans text-sm font-medium text-[#FAF9F6] transition hover:bg-[#2A4C7A] active:scale-[0.98]"
          >
            Start writing
          </a>
        </div>
      </header>

      {/* Hero: manifesto type, oversized, with an offset photo strip */}
      <section className="mx-auto max-w-6xl px-5 pt-14 pb-24 lg:px-8">
        <p className="font-sans text-[11px] font-medium uppercase tracking-[0.22em] text-[#1F3A5F]">
          A notebook with margins
        </p>
        <h1 className="mt-6 max-w-[15ch] text-6xl font-semibold leading-[1.06] tracking-tight md:text-8xl">
          Notes are the drafts of a <em className="italic leading-[1.1]">mind</em>.
        </h1>
        <p className="mt-8 max-w-[52ch] font-sans text-lg leading-relaxed text-[#5C5A52]">
          Marginalia keeps what you write in one long book you are always reading, and lets the
          margins fill themselves.
        </p>
        <a
          href="#start"
          className="mt-9 inline-block rounded-sm bg-[#1F3A5F] px-6 py-3 font-sans text-sm font-medium text-[#FAF9F6] transition hover:bg-[#2A4C7A] active:scale-[0.98]"
        >
          Start writing
        </a>

        <div className="mt-20 grid grid-cols-2 gap-4 md:grid-cols-12">
          <Reveal className="col-span-1 md:col-span-5 md:translate-y-10">
            <img
              src="https://picsum.photos/seed/marginalia-paper-margin/900/1150"
              alt="A page with wide handwritten margins"
              width={900}
              height={1150}
              className="aspect-[9/11] w-full rounded-sm object-cover"
            />
          </Reveal>
          <Reveal delay={0.1} className="col-span-1 md:col-span-4 md:-translate-y-4">
            <img
              src="https://picsum.photos/seed/marginalia-library-stacks/1000/620"
              alt="Stacked books on a reading table"
              width={1000}
              height={620}
              className="aspect-[16/10] w-full rounded-sm object-cover"
            />
          </Reveal>
          <Reveal delay={0.18} className="col-span-2 md:col-span-3 md:translate-y-16">
            <img
              src="https://picsum.photos/seed/marginalia-ink-bottle/800/800"
              alt="An ink bottle beside a pen"
              width={800}
              height={800}
              className="aspect-square w-full rounded-sm object-cover"
            />
          </Reveal>
        </div>
      </section>

      {/* Three movements, stacked and indented like manuscript rubrics */}
      <section id="method" className="scroll-mt-20 border-t border-[#E4E1D8]">
        <div className="mx-auto max-w-6xl px-5 py-24 md:py-28 lg:px-8">
          <h2 className="max-w-[20ch] text-4xl font-semibold tracking-tight md:text-5xl">
            The book reads itself in three movements.
          </h2>
          <div className="mt-16 space-y-16">
            {MOVEMENTS.map((m, i) => (
              <Reveal key={m.verb} delay={i * 0.06} className={`${m.indent} max-w-[54ch]`}>
                <p className="text-[28px] font-semibold italic leading-[1.15] tracking-tight text-[#1F3A5F] pb-1">
                  {m.verb}
                </p>
                <p className="mt-3 font-sans text-[16px] leading-relaxed text-[#5C5A52]">{m.body}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Statement band */}
      <section className="border-y border-[#E4E1D8] bg-[#F2EFE8]">
        <div className="mx-auto max-w-6xl px-5 py-24 text-center md:py-28 lg:px-8">
          <Reveal>
            <p className="mx-auto max-w-[24ch] text-4xl font-semibold leading-[1.12] tracking-tight md:text-6xl">
              Write it small. It grows in the <em className="italic leading-[1.1] pb-1">margins</em>.
            </p>
          </Reveal>
        </div>
      </section>

      {/* Clean split: message and portrait, aligned */}
      <section className="mx-auto grid max-w-6xl items-center gap-12 px-5 py-24 md:grid-cols-2 md:py-28 lg:px-8">
        <Reveal>
          <h2 className="max-w-[16ch] text-4xl font-semibold tracking-tight md:text-5xl">
            A page that answers back.
          </h2>
          <p className="mt-6 max-w-[48ch] font-sans text-[16px] leading-relaxed text-[#5C5A52]">
            Marginalia reads your archive the way a patient editor would. It quotes you back to
            yourself, in your own handwriting, at the right paragraph.
          </p>
          <a
            href="#start"
            className="mt-8 inline-block border-b border-[#1F3A5F] pb-0.5 font-sans text-sm font-medium text-[#1F3A5F] transition hover:border-[#20201D] hover:text-[#20201D]"
          >
            Start writing
          </a>
        </Reveal>
        <Reveal delay={0.1} y={32}>
          <img
            src="https://picsum.photos/seed/marginalia-handwriting-ink/900/1100"
            alt="Handwriting in progress on a ruled page"
            width={900}
            height={1100}
            className="aspect-[9/11] w-full rounded-sm object-cover"
          />
        </Reveal>
      </section>

      {/* What people keep: two grouped clusters, not a hairline list */}
      <section id="kept" className="scroll-mt-20 border-t border-[#E4E1D8]">
        <div className="mx-auto max-w-6xl px-5 py-24 md:py-28 lg:px-8">
          <h2 className="text-4xl font-semibold tracking-tight md:text-5xl">What people keep here</h2>
          <div className="mt-14 grid gap-14 md:grid-cols-2">
            {KEPT.map((k, i) => (
              <Reveal key={k.group} delay={i * 0.08}>
                <h3 className="border-t border-[#20201D] pt-4 text-xl font-semibold tracking-tight">
                  {k.group}
                </h3>
                <ul className="mt-6 space-y-4 font-sans text-[15px] leading-snug text-[#5C5A52]">
                  {k.items.map((item) => (
                    <li key={item} className="max-w-[44ch]">
                      {item}
                    </li>
                  ))}
                </ul>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Close */}
      <section id="start" className="scroll-mt-20 border-t border-[#E4E1D8]">
        <div className="mx-auto max-w-6xl px-5 py-28 text-center md:py-32 lg:px-8">
          <Reveal>
            <h2 className="mx-auto max-w-[18ch] text-4xl font-semibold tracking-tight md:text-6xl">
              The margin is open. Take a pen.
            </h2>
            <a
              href="#"
              className="mt-9 inline-block rounded-sm bg-[#1F3A5F] px-6 py-3 font-sans text-sm font-medium text-[#FAF9F6] transition hover:bg-[#2A4C7A] active:scale-[0.98]"
            >
              Start writing
            </a>
          </Reveal>
        </div>
      </section>

      <footer className="border-t border-[#E4E1D8]">
        <div className="mx-auto flex max-w-6xl flex-col justify-between gap-6 px-5 py-10 md:flex-row md:items-center lg:px-8">
          <p className="font-sans text-sm text-[#5C5A52]">Marginalia. Notes in the margin since the first drafts.</p>
          <nav className="flex items-center gap-8 font-sans text-sm text-[#5C5A52]">
            <a href="#method" className="hover:text-[#20201D]">Method</a>
            <a href="#kept" className="hover:text-[#20201D]">What people keep</a>
            <a href="#start" className="text-[#1F3A5F] hover:text-[#20201D]">Start writing</a>
          </nav>
        </div>
      </footer>
    </div>
  );
});
