// Fathom. Linear-clean SaaS language. Dials: V6 / M4 / D3.
// Theme: light with system dark variant (Tailwind dark:).
// Shape rule (locked): interactive = pill, media = 2xl radius, tiles = xl radius.
import { memo } from "react";
import { motion, useReducedMotion } from "motion/react";
import { ArrowRight, ArrowDown, CalendarBlank, MagnifyingGlass } from "@phosphor-icons/react";
import { Reveal, Monogram, EASE } from "../ui";

const NAV = [
  { label: "Method", href: "#method" },
  { label: "Features", href: "#features" },
  { label: "Sign in", href: "#" },
];

const LOGOS = ["H", "P", "C", "N", "F"];

const MOVES = [
  {
    verb: "Capture",
    body: "One shortcut, anywhere. A thought lands in Fathom in under a second, with zero decisions about folders.",
  },
  {
    verb: "Connect",
    body: "Fathom suggests links as you write, from the notes you took last month about the same idea.",
  },
  {
    verb: "Recall",
    body: "Search by meaning, not spelling. Yesterday's half-thought resurfaces the moment you need it.",
  },
];

export default memo(function Fathom() {
  const reduce = useReducedMotion();
  return (
    <div className="min-h-[100dvh] bg-white font-sans text-zinc-900 antialiased dark:bg-zinc-950 dark:text-zinc-100">
      <header className="sticky top-0 z-40 h-16 border-b border-zinc-200/70 bg-white/80 backdrop-blur-md dark:border-zinc-800/70 dark:bg-zinc-950/80">
        <div className="mx-auto flex h-full max-w-6xl items-center justify-between px-5 lg:px-8">
          <a href="#" className="text-[15px] font-semibold tracking-tight">
            Fathom
          </a>
          <nav className="hidden items-center gap-7 text-sm text-zinc-600 md:flex dark:text-zinc-400">
            {NAV.map((n) => (
              <a key={n.label} href={n.href} className="transition-colors hover:text-zinc-900 dark:hover:text-zinc-100">
                {n.label}
              </a>
            ))}
          </nav>
          <a
            href="#get"
            className="rounded-full bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500 active:scale-[0.98]"
          >
            Get started
          </a>
        </div>
      </header>

      {/* Hero: asymmetric split, text left, media right */}
      <section className="mx-auto grid max-w-6xl items-center gap-12 px-5 pt-12 pb-20 md:grid-cols-12 md:pt-16 md:pb-28 lg:px-8">
        <div className="md:col-span-7">
          {!reduce && (
            <motion.p
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: EASE }}
              className="text-[11px] font-medium uppercase tracking-[0.18em] text-blue-600 dark:text-blue-400"
            >
              Second brain, tidied
            </motion.p>
          )}
          <motion.h1
            initial={reduce ? false : { opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.05, ease: EASE }}
            className="mt-4 text-5xl font-semibold leading-[1.02] tracking-tight md:text-6xl lg:text-7xl"
          >
            The notebook that thinks back.
          </motion.h1>
          <motion.p
            initial={reduce ? false : { opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.12, ease: EASE }}
            className="mt-6 max-w-[52ch] text-lg leading-relaxed text-zinc-600 dark:text-zinc-400"
          >
            Capture fast, connect naturally, recall years later. Fathom turns scattered notes into
            a body of work.
          </motion.p>
          <motion.div
            initial={reduce ? false : { opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.18, ease: EASE }}
            className="mt-8 flex flex-wrap items-center gap-3"
          >
            <a
              href="#get"
              className="group inline-flex items-center gap-2 rounded-full bg-blue-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-blue-500 active:scale-[0.98]"
            >
              Get started
              <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />
            </a>
            <a
              href="#method"
              className="inline-flex items-center gap-2 rounded-full border border-zinc-300 px-5 py-2.5 text-sm font-medium text-zinc-700 transition hover:border-zinc-400 hover:bg-zinc-50 active:scale-[0.98] dark:border-zinc-700 dark:text-zinc-300 dark:hover:border-zinc-600 dark:hover:bg-zinc-900"
            >
              See how it works
              <ArrowDown size={16} />
            </a>
          </motion.div>
        </div>
        <motion.div
          initial={reduce ? false : { opacity: 0, scale: 0.97, y: 24 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.1, ease: EASE }}
          className="md:col-span-5 md:translate-y-6"
        >
          <img
            src="https://picsum.photos/seed/fathom-notebook-desk/1000/1200"
            alt="A quiet desk with an open notebook"
            width={1000}
            height={1200}
            className="aspect-[4/5] w-full rounded-2xl object-cover shadow-[0_30px_80px_-20px_rgb(37_99_235/0.25)] ring-1 ring-zinc-900/10 dark:ring-white/10"
          />
        </motion.div>
      </section>

      {/* Logo wall, below the hero */}
      <section className="border-t border-zinc-200 dark:border-zinc-800">
        <div className="mx-auto max-w-6xl px-5 py-12 lg:px-8">
          <p className="text-sm text-zinc-500 dark:text-zinc-500">
            Teams that keep their thinking in Fathom
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-x-12 gap-y-6 text-zinc-400 dark:text-zinc-600">
            {LOGOS.map((m) => (
              <Monogram key={m} mark={m} className="h-10 w-10 transition-colors hover:text-zinc-700 dark:hover:text-zinc-300" />
            ))}
          </div>
        </div>
      </section>

      {/* Method: offset three-column hairline row, first column dominant */}
      <section id="method" className="mx-auto max-w-6xl scroll-mt-20 px-5 py-24 md:py-32 lg:px-8">
        <Reveal>
          <h2 className="max-w-[18ch] text-4xl font-semibold tracking-tight md:text-5xl">
            Three moves, one habit.
          </h2>
        </Reveal>
        <div className="mt-14 grid gap-px overflow-hidden md:grid-cols-[1.4fr_1fr_1fr]">
          {MOVES.map((m, i) => (
            <Reveal key={m.verb} delay={i * 0.08} className="border-t border-zinc-200 pt-6 md:pr-8 dark:border-zinc-800">
              <p className="text-xl font-semibold tracking-tight text-blue-600 dark:text-blue-400">{m.verb}</p>
              <p className="mt-3 max-w-[34ch] text-[15px] leading-relaxed text-zinc-600 dark:text-zinc-400">
                {m.body}
              </p>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Features: bento, 3 items -> 3 cells, one image + one tinted */}
      <section id="features" className="mx-auto max-w-6xl scroll-mt-20 px-5 pb-24 md:pb-32 lg:px-8">
        <div className="grid gap-4 md:grid-cols-5">
          <Reveal className="md:col-span-3 md:row-span-2">
            <figure className="flex h-full flex-col overflow-hidden rounded-xl bg-zinc-50 ring-1 ring-zinc-200 dark:bg-zinc-900 dark:ring-zinc-800">
              <img
                src="https://picsum.photos/seed/fathom-backlinks-graph/1200/760"
                alt="Interconnected papers suggesting a link graph"
                width={1200}
                height={760}
                className="aspect-[1200/760] w-full object-cover"
              />
              <figcaption className="p-7">
                <p className="text-lg font-semibold tracking-tight">Backlinks that build themselves</p>
                <p className="mt-2 max-w-[46ch] text-[15px] leading-relaxed text-zinc-600 dark:text-zinc-400">
                  Every note remembers where it came from, and everything that referred to it.
                </p>
              </figcaption>
            </figure>
          </Reveal>
          <Reveal delay={0.1} className="md:col-span-2">
            <div className="flex h-full flex-col justify-center rounded-xl bg-blue-50 p-7 ring-1 ring-blue-100 dark:bg-blue-950/40 dark:ring-blue-900/50">
              <CalendarBlank size={26} weight="regular" className="text-blue-600 dark:text-blue-400" />
              <p className="mt-4 text-lg font-semibold tracking-tight">Daily notes with memory</p>
              <p className="mt-2 max-w-[40ch] text-[15px] leading-relaxed text-zinc-600 dark:text-zinc-400">
                A fresh page every morning that already knows what you were working on.
              </p>
            </div>
          </Reveal>
          <Reveal delay={0.16} className="md:col-span-2">
            <div className="flex h-full flex-col justify-center rounded-xl bg-zinc-50 p-7 ring-1 ring-zinc-200 dark:bg-zinc-900 dark:ring-zinc-800">
              <MagnifyingGlass size={26} weight="regular" className="text-blue-600 dark:text-blue-400" />
              <p className="mt-4 text-lg font-semibold tracking-tight">Search that forgives typos</p>
              <p className="mt-2 max-w-[40ch] text-[15px] leading-relaxed text-zinc-600 dark:text-zinc-400">
                Instant, offline, semantic. Like autocomplete for your own memory.
              </p>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Quote */}
      <section className="border-t border-zinc-200 dark:border-zinc-800">
        <div className="mx-auto max-w-6xl px-5 py-24 md:py-28 lg:px-8">
          <Reveal>
            <blockquote className="max-w-[46ch] text-2xl leading-snug tracking-tight md:text-3xl">
              &ldquo;I stopped keeping notes in five places. Fathom is the first second brain I
              actually trust to remember for me.&rdquo;
            </blockquote>
            <p className="mt-6 text-sm text-zinc-500 dark:text-zinc-500">
              Ilse Brandt
              <span className="mx-2 text-zinc-300 dark:text-zinc-700">/</span>
              Head of Research, Halden Systems
            </p>
          </Reveal>
        </div>
      </section>

      {/* Final CTA */}
      <section id="get" className="scroll-mt-20 border-t border-zinc-200 dark:border-zinc-800">
        <div className="mx-auto max-w-6xl px-5 py-28 text-center md:py-36 lg:px-8">
          <Reveal>
            <h2 className="mx-auto max-w-[16ch] text-4xl font-semibold tracking-tight md:text-6xl">
              Your best ideas deserve a better address.
            </h2>
            <a
              href="#"
              className="mt-9 inline-flex items-center gap-2 rounded-full bg-blue-600 px-6 py-3 text-sm font-medium text-white transition hover:bg-blue-500 active:scale-[0.98]"
            >
              Get started
              <ArrowRight size={16} />
            </a>
          </Reveal>
        </div>
      </section>

      <footer className="border-t border-zinc-200 dark:border-zinc-800">
        <div className="mx-auto flex max-w-6xl flex-col justify-between gap-8 px-5 py-12 md:flex-row md:items-center lg:px-8">
          <div>
            <p className="text-[15px] font-semibold tracking-tight">Fathom</p>
            <p className="mt-2 max-w-[36ch] text-sm text-zinc-500 dark:text-zinc-500">
              A second brain for people who think for a living.
            </p>
          </div>
          <nav className="flex items-center gap-8 text-sm text-zinc-600 dark:text-zinc-400">
            <a href="#method" className="hover:text-zinc-900 dark:hover:text-zinc-100">Method</a>
            <a href="#features" className="hover:text-zinc-900 dark:hover:text-zinc-100">Features</a>
            <a href="#get" className="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">Get started</a>
          </nav>
        </div>
      </footer>
    </div>
  );
});
