// mnemo. Dark-tech / terminal language for terminal-dweller note nerds. Dials: V8 / M6 / D4.
// Theme lock: dark only (deliberate art direction for this iteration).
// Shape rule (locked): all-sharp, radius 0 everywhere. Accent lock: emerald.
import { memo } from "react";
import { Reveal } from "../ui";

const KEYS = [
  { chord: "⌘K", what: "open the brain" },
  { chord: "⌘⇧N", what: "new node" },
  { chord: "⌘O", what: "quick switch" },
  { chord: "⌘⇧L", what: "link selection" },
  { chord: "⌘P", what: "command palette" },
  { chord: "⌘S", what: "sync to vault" },
];

const LINKS = [
  {
    title: "why queues beat batch jobs",
    context: "written after the March incident, still cited in every design doc since",
  },
  {
    title: "what my grandfather called patience",
    context: "overheard, typed on the train, found again in a debugging session",
  },
  {
    title: "postgres upgrade postmortem",
    context: "linked from eleven notes, the graph pulled it out of the archive",
  },
  {
    title: "routines worth keeping at 5am",
    context: "backlinks to sleep, coffee, and one very stubborn queue",
  },
];

const MARQUEE_ITEMS = [
  "GREP YOUR OWN MIND  //  ",
  "BACKLINKS POINT BOTH WAYS  //  ",
  "PLAIN MARKDOWN, NO LOCK-IN  //  ",
  "KEYBOARD, NEVER MOUSE  //  ",
  "WORKS ON A PLANE  //  ",
];

export default memo(function Mnemo() {
  return (
    <div className="min-h-[100dvh] bg-zinc-950 font-sans text-zinc-300 antialiased selection:bg-emerald-400/30 selection:text-emerald-100">
      <header className="sticky top-0 z-40 h-16 border-b border-zinc-800/80 bg-zinc-950/85 backdrop-blur-md">
        <div className="mx-auto flex h-full max-w-6xl items-center justify-between px-5 lg:px-8">
          <a href="#" className="font-mono text-[15px] font-semibold tracking-tight text-zinc-50">
            mnemo<span className="text-emerald-400">//</span>
          </a>
          <nav className="hidden items-center gap-7 font-mono text-[13px] text-zinc-500 md:flex">
            <a href="#keys" className="transition-colors hover:text-emerald-400">keys</a>
            <a href="#graph" className="transition-colors hover:text-emerald-400">graph</a>
            <a href="#links" className="transition-colors hover:text-emerald-400">links</a>
          </nav>
          <a
            href="#install"
            className="rounded-none border border-emerald-400/70 bg-emerald-400/10 px-4 py-2 font-mono text-[13px] font-medium text-emerald-300 transition hover:bg-emerald-400/20 active:scale-[0.98]"
          >
            install
          </a>
        </div>
      </header>

      {/* Hero: left-aligned dominant, media right */}
      <section className="mx-auto grid max-w-6xl items-center gap-12 px-5 pt-16 pb-20 md:grid-cols-12 md:pt-20 lg:px-8">
        <div className="md:col-span-7">
          <h1 className="max-w-[13ch] text-5xl font-semibold leading-[1.04] tracking-tight text-zinc-50 md:text-6xl lg:text-[68px]">
            Notes are nodes. Memory is a <span className="text-emerald-400">graph</span>.
          </h1>
          <p className="mt-6 max-w-[46ch] font-mono text-[15px] leading-relaxed text-zinc-400">
            Plain files, real backlinks, a keyboard you never leave. A second brain for terminal
            dwellers.
          </p>
          <div className="mt-9 flex flex-wrap items-center gap-4">
            <a
              href="#install"
              className="rounded-none bg-emerald-400 px-6 py-3 font-mono text-sm font-semibold text-zinc-950 transition hover:bg-emerald-300 active:scale-[0.98]"
            >
              $ install mnemo
            </a>
            <a
              href="#keys"
              className="rounded-none border border-zinc-700 px-6 py-3 font-mono text-sm text-zinc-300 transition hover:border-zinc-500 hover:bg-zinc-900 active:scale-[0.98]"
            >
              read the docs
            </a>
          </div>
        </div>
        <Reveal className="md:col-span-5" y={32}>
          <img
            src="https://picsum.photos/seed/mnemo-graph-night-desk/1100/1300"
            alt="A dim desk lit by a screen at night"
            width={1100}
            height={1300}
            className="aspect-[11/13] w-full rounded-none object-cover opacity-90 ring-1 ring-zinc-800"
          />
        </Reveal>
      </section>

      {/* The page's one marquee band */}
      <div className="marquee border-y border-zinc-800/80 py-4">
        <div className="marquee-track">
          {[...MARQUEE_ITEMS, ...MARQUEE_ITEMS].map((item, i) => (
            <span key={i} className="shrink-0 whitespace-nowrap font-mono text-[13px] tracking-[0.2em] text-zinc-600">
              {item}
            </span>
          ))}
        </div>
      </div>

      {/* Keys */}
      <section id="keys" className="mx-auto max-w-6xl scroll-mt-20 px-5 py-24 md:py-28 lg:px-8">
        <Reveal>
          <h2 className="max-w-[22ch] text-3xl font-semibold tracking-tight text-zinc-50 md:text-5xl">
            The whole brain, reachable by chord.
          </h2>
        </Reveal>
        <div className="mt-12 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {KEYS.map((k, i) => (
            <Reveal
              key={k.chord}
              delay={i * 0.05}
              className="group flex items-center justify-between border border-zinc-800 bg-zinc-900/40 px-5 py-4 transition-colors hover:border-emerald-400/50"
            >
              <kbd className="bg-transparent font-mono text-lg text-emerald-300">{k.chord}</kbd>
              <span className="font-mono text-[13px] text-zinc-500 transition-colors group-hover:text-zinc-300">
                {k.what}
              </span>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Full-bleed graph image */}
      <section id="graph" className="relative scroll-mt-20 border-y border-zinc-800/80">
        <Reveal y={0} className="h-[58vh] overflow-hidden md:h-[70vh]">
          <img
            src="https://picsum.photos/seed/mnemo-node-graph-macro/1800/1000"
            alt="Abstract macro texture suggesting a network"
            width={1800}
            height={1000}
            className="h-full w-full object-cover opacity-80"
          />
        </Reveal>
        <div className="mx-auto max-w-6xl px-5 py-10 lg:px-8">
          <p className="max-w-[52ch] font-mono text-[15px] leading-relaxed text-zinc-500">
            Five thousand notes, one graph. Zoom to a decade of thinking, or grep a single
            afternoon.
          </p>
        </div>
      </section>

      {/* Backlinks list, no hairline per row */}
      <section id="links" className="mx-auto max-w-6xl scroll-mt-20 px-5 py-24 md:py-28 lg:px-8">
        <Reveal>
          <h2 className="max-w-[24ch] text-3xl font-semibold tracking-tight text-zinc-50 md:text-5xl">
            Your notes already link to each other. mnemo just shows you.
          </h2>
        </Reveal>
        <ul className="mt-12 space-y-8">
          {LINKS.map((l, i) => (
            <Reveal key={l.title} delay={i * 0.06}>
              <li className="group border-l-2 border-zinc-800 pl-6 transition-all hover:translate-x-1 hover:border-emerald-400">
                <p className="font-mono text-lg text-zinc-100">
                  <span className="mr-2 text-emerald-400">↳</span>
                  {l.title}
                </p>
                <p className="mt-1 max-w-[60ch] pl-6 font-mono text-[13px] text-zinc-500">{l.context}</p>
              </li>
            </Reveal>
          ))}
        </ul>
      </section>

      {/* Quote */}
      <section className="border-t border-zinc-800/80">
        <div className="mx-auto max-w-6xl px-5 py-24 lg:px-8">
          <Reveal>
            <blockquote className="max-w-[48ch] font-mono text-xl leading-relaxed text-zinc-300 md:text-2xl">
              &ldquo;I found a note I wrote four years ago because a bug from last week pointed at
              it. That is the whole product.&rdquo;
            </blockquote>
            <p className="mt-6 font-mono text-[13px] text-zinc-500">
              Théo Marchand <span className="mx-2 text-zinc-700">/</span> systems engineer, Ghent
            </p>
          </Reveal>
        </div>
      </section>

      {/* Install CTA */}
      <section id="install" className="scroll-mt-20 border-t border-zinc-800/80">
        <div className="mx-auto max-w-6xl px-5 py-28 md:py-32 lg:px-8">
          <Reveal>
            <h2 className="max-w-[16ch] text-4xl font-semibold tracking-tight text-zinc-50 md:text-6xl">
              Give your memory a filesystem.
            </h2>
            <a
              href="#"
              className="mt-9 inline-block rounded-none bg-emerald-400 px-7 py-3.5 font-mono text-sm font-semibold text-zinc-950 transition hover:bg-emerald-300 active:scale-[0.98]"
            >
              $ install mnemo
            </a>
          </Reveal>
        </div>
      </section>

      <footer className="border-t border-zinc-800/80">
        <div className="mx-auto flex max-w-6xl flex-col justify-between gap-6 px-5 py-10 md:flex-row md:items-center lg:px-8">
          <p className="font-mono text-sm text-zinc-500">
            mnemo<span className="text-emerald-400">//</span> your thoughts, versioned
          </p>
          <nav className="flex items-center gap-8 font-mono text-[13px] text-zinc-500">
            <a href="#keys" className="hover:text-emerald-400">keys</a>
            <a href="#links" className="hover:text-emerald-400">links</a>
            <a href="#install" className="text-emerald-400">install</a>
          </nav>
        </div>
      </footer>
    </div>
  );
});
