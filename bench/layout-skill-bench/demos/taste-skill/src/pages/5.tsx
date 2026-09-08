// Attic. Cold-luxury language: silver-grey, smoke, chrome, ink. Dials: V7 / M5 / D3.
// Theme lock: light cold-luxury (deliberate art direction for this iteration).
// Shape rule (locked): interactive = pill, media and tiles = rounded-2xl. No accent: monochrome + chrome.
// .glass below is a web frosted-glass approximation (backdrop-filter + layered borders),
// not official Apple Liquid Glass, with a solid fallback for prefers-reduced-transparency.
import { memo } from "react";
import { motion, useReducedMotion } from "motion/react";
import { ArrowRight } from "@phosphor-icons/react";
import { Reveal, EASE } from "../ui";

const ROWS = [
  {
    term: "One drawer",
    body: "Notes, marks, fragments. Everything lives in one stack, ordered by when you last needed it.",
  },
  {
    term: "Returned",
    body: "Attic resurfaces old notes inside new ones, like a librarian who knows your taste.",
  },
  {
    term: "Locked",
    body: "End-to-end encrypted, keys held only by you. Even we cannot read the room.",
  },
];

export default memo(function Attic() {
  const reduce = useReducedMotion();
  return (
    <div className="min-h-[100dvh] bg-[#F4F5F7] font-elegant text-[#17191C] antialiased">
      <header className="sticky top-0 z-40 h-16 border-b border-[#17191C]/10 bg-[#F4F5F7]/80 backdrop-blur-md">
        <div className="mx-auto flex h-full max-w-6xl items-center justify-between px-5 lg:px-8">
          <a href="#" className="text-[15px] font-semibold tracking-[0.02em]">
            Attic
          </a>
          <nav className="hidden items-center gap-8 text-sm text-[#5D6167] md:flex">
            <a href="#room" className="transition-colors hover:text-[#17191C]">The room</a>
            <a href="#kept" className="transition-colors hover:text-[#17191C]">Kept</a>
          </nav>
          <a
            href="#start"
            className="rounded-full bg-[#17191C] px-4.5 py-2 text-sm font-medium text-[#F4F5F7] transition hover:bg-[#33373D] active:scale-[0.98]"
          >
            Try Attic
          </a>
        </div>
      </header>

      {/* Hero: full-bleed photograph with a glass panel, web glass approximation */}
      <section className="relative min-h-[88dvh] overflow-hidden">
        <img
          src="https://picsum.photos/seed/attic-light-room-dust/1900/1200"
          alt="Light falling across a quiet storage room"
          width={1900}
          height={1200}
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-[#F4F5F7]/70 via-[#F4F5F7]/20 to-transparent" />
        <div className="relative mx-auto flex min-h-[88dvh] max-w-6xl items-center px-5 py-16 lg:px-8">
          <motion.div
            initial={reduce ? false : { opacity: 0, y: 28 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: EASE }}
            className="glass w-full max-w-xl rounded-2xl p-10 md:p-12"
          >
            <h1 className="max-w-[14ch] text-5xl font-semibold leading-[1.05] tracking-tight md:text-6xl">
              A quiet room for everything you think.
            </h1>
            <p className="mt-6 max-w-[44ch] text-[17px] leading-relaxed text-[#4A4E54]">
              Attic keeps every note in one calm place and hands it back the moment you ask.
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-4">
              <a
                href="#start"
                className="group inline-flex items-center gap-2 rounded-full bg-[#17191C] px-6 py-3 text-sm font-medium text-[#F4F5F7] transition hover:bg-[#33373D] active:scale-[0.98]"
              >
                Try Attic
                <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />
              </a>
              <a
                href="#room"
                className="rounded-full border border-[#17191C]/25 bg-white/40 px-6 py-3 text-sm font-medium text-[#17191C] transition backdrop-blur-sm hover:bg-white/70 active:scale-[0.98]"
              >
                Take the tour
              </a>
            </div>
          </motion.div>
        </div>
      </section>

      {/* The room: term-and-definition rows, one hairline between */}
      <section id="room" className="mx-auto max-w-6xl scroll-mt-20 px-5 py-24 md:py-28 lg:px-8">
        <Reveal>
          <h2 className="max-w-[20ch] text-4xl font-semibold tracking-tight md:text-5xl">
            The room, explained plainly.
          </h2>
        </Reveal>
        <dl className="mt-14 divide-y divide-[#17191C]/10">
          {ROWS.map((r, i) => (
            <Reveal key={r.term} delay={i * 0.06}>
              <div className="grid gap-3 py-8 md:grid-cols-[1fr_2fr] md:gap-10">
                <dt className="text-lg font-semibold tracking-tight">{r.term}</dt>
                <dd className="max-w-[56ch] text-[16px] leading-relaxed text-[#4A4E54]">{r.body}</dd>
              </div>
            </Reveal>
          ))}
        </dl>
      </section>

      {/* Kept: asymmetric photo pair, images speak alone */}
      <section id="kept" className="mx-auto max-w-6xl scroll-mt-20 px-5 pb-24 md:pb-28 lg:px-8">
        <Reveal>
          <h2 className="max-w-[18ch] text-4xl font-semibold tracking-tight md:text-5xl">
            Everything you kept, kept well.
          </h2>
        </Reveal>
        <div className="mt-14 grid gap-4 md:grid-cols-12">
          <Reveal className="md:col-span-7">
            <img
              src="https://picsum.photos/seed/attic-afternoon-boxes/1200/760"
              alt="Boxes waiting quietly in afternoon light"
              width={1200}
              height={760}
              className="aspect-[16/10] w-full rounded-2xl object-cover"
            />
          </Reveal>
          <Reveal delay={0.1} className="md:col-span-5">
            <img
              src="https://picsum.photos/seed/attic-window-dust-motes/900/1200"
              alt="Dust in a beam of light from a small window"
              width={900}
              height={1200}
              className="h-full w-full rounded-2xl object-cover"
            />
          </Reveal>
        </div>
      </section>

      {/* Quote */}
      <section className="border-t border-[#17191C]/10 bg-[#EDEEF1]">
        <div className="mx-auto max-w-6xl px-5 py-24 md:py-28 lg:px-8">
          <Reveal>
            <blockquote className="max-w-[42ch] text-2xl leading-snug tracking-tight md:text-[32px]">
              &ldquo;Everything else gets lost. Attic is the one shelf that never lets me
              down.&rdquo;
            </blockquote>
            <p className="mt-6 text-sm text-[#5D6167]">
              Clara Osei-Bonsu
              <span className="mx-2 text-[#17191C]/25">/</span>
              archivist, London
            </p>
          </Reveal>
        </div>
      </section>

      {/* Start CTA, chrome panel */}
      <section id="start" className="mx-auto max-w-6xl scroll-mt-20 px-5 py-24 md:py-28 lg:px-8">
        <Reveal>
          <div className="glass flex flex-col items-start justify-between gap-8 rounded-2xl p-10 md:flex-row md:items-center md:p-12">
            <h2 className="max-w-[16ch] text-3xl font-semibold tracking-tight md:text-4xl">
              One room. One price. Eight euros a month.
            </h2>
            <a
              href="#"
              className="shrink-0 rounded-full bg-[#17191C] px-7 py-3.5 text-sm font-medium text-[#F4F5F7] transition hover:bg-[#33373D] active:scale-[0.98]"
            >
              Try Attic
            </a>
          </div>
        </Reveal>
      </section>

      <footer className="border-t border-[#17191C]/10">
        <div className="mx-auto flex max-w-6xl flex-col justify-between gap-6 px-5 py-10 md:flex-row md:items-center lg:px-8">
          <p className="text-sm text-[#5D6167]">Attic. The upstairs your thinking deserves.</p>
          <nav className="flex items-center gap-8 text-sm text-[#5D6167]">
            <a href="#room" className="transition-colors hover:text-[#17191C]">The room</a>
            <a href="#kept" className="transition-colors hover:text-[#17191C]">Kept</a>
            <a href="#start" className="font-medium text-[#17191C]">Try Attic</a>
          </nav>
        </div>
      </footer>
    </div>
  );
});
