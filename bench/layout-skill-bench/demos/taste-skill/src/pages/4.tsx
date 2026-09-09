// Sift. Bold playful consumer language. Dials: V9 / M7 / D4.
// Theme lock: paper + ink + one burnt-orange accent (deliberate art direction for this iteration).
// Shape rule (locked): interactive = full pill, media = rounded-3xl. Accent lock: #E2552C.
import { memo } from "react";
import { motion, useReducedMotion } from "motion/react";
import { ArrowRight, Tray, Link, ChatCircleDots, SpeakerHigh, AirplaneTilt } from "@phosphor-icons/react";
import { Reveal, EASE } from "../ui";

const DISPLAY =
  "font-display font-extrabold uppercase tracking-tight [font-variation-settings:'wdth'_112]";

const FEATURES = [
  {
    icon: Tray,
    name: "Inbox for everything",
    line: "Text, voice, photos of whiteboards. Sift catches it all in one pile.",
    img: "sift-feature-inbox-pile",
  },
  {
    icon: Link,
    name: "Links, free",
    line: "Every note knows its cousins. Backlinks cost nothing, ever.",
    img: "sift-feature-links-threads",
  },
  {
    icon: ChatCircleDots,
    name: "Find, not search",
    line: "Type half a memory. Sift guesses the rest of the feeling.",
    img: "sift-feature-find-magnify",
  },
  {
    icon: SpeakerHigh,
    name: "Voice in",
    line: "Mumble it on the walk home. It lands as a tidy note by your desk.",
    img: "sift-feature-voice-walk",
  },
  {
    icon: AirplaneTilt,
    name: "Works in the woods",
    line: "No signal, no problem. The whole brain lives in your pocket.",
    img: "sift-feature-offline-woods",
  },
];

const QUOTES = [
  {
    text: "My old notes app was a museum. Sift is a kitchen. Everything in here is still in use.",
    name: "Priya Raghunathan",
    role: "structural engineer",
  },
  {
    text: "I dump ideas in half-asleep and find them sharp the next morning. Suspiciously good.",
    name: "Tomás Beira",
    role: "documentary editor",
  },
];

export default memo(function Sift() {
  const reduce = useReducedMotion();
  return (
    <div className="min-h-[100dvh] bg-[#F6F5F3] font-display text-[#141311] antialiased">
      <header className="sticky top-0 z-40 h-16 border-b border-[#E3E0DA] bg-[#F6F5F3]/90 backdrop-blur-md">
        <div className="mx-auto flex h-full max-w-7xl items-center justify-between px-5 lg:px-8">
          <a href="#" className={`${DISPLAY} text-2xl`}>
            Sift<span className="text-[#E2552C]">.</span>
          </a>
          <nav className="hidden items-center gap-8 text-[13px] font-semibold uppercase tracking-wide text-[#5A564E] md:flex">
            <a href="#features" className="transition-colors hover:text-[#141311]">Features</a>
            <a href="#voices" className="transition-colors hover:text-[#141311]">Voices</a>
          </nav>
          <a
            href="#get"
            className="rounded-full bg-[#E2552C] px-5 py-2 text-sm font-bold text-[#141311] transition hover:brightness-105 active:scale-[0.98]"
          >
            Get Sift
          </a>
        </div>
      </header>

      {/* Hero: oversized type left, tilted photo collage right */}
      <section className="mx-auto grid max-w-7xl items-center gap-14 px-5 pt-12 pb-24 md:grid-cols-12 md:pt-16 lg:px-8">
        <div className="md:col-span-7">
          <motion.h1
            initial={reduce ? false : { opacity: 0, y: 26 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: EASE }}
            className={`${DISPLAY} text-[56px] leading-[0.95] md:text-8xl lg:text-[104px]`}
          >
            Notes you can <span className="bg-[#E2552C] px-3 leading-[1.1]">find</span> again.
          </motion.h1>
          <motion.p
            initial={reduce ? false : { opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1, ease: EASE }}
            className="mt-7 max-w-[42ch] font-sans text-lg leading-relaxed text-[#5A564E]"
          >
            Throw thoughts in, sift them later. A second brain with a sieve instead of a landfill.
          </motion.p>
          <motion.div
            initial={reduce ? false : { opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.16, ease: EASE }}
            className="mt-9 flex flex-wrap items-center gap-4"
          >
            <a
              href="#get"
              className="group inline-flex items-center gap-2 rounded-full bg-[#141311] px-6 py-3.5 text-sm font-bold text-[#F6F5F3] transition hover:bg-[#2A2721] active:scale-[0.98]"
            >
              Get Sift
              <ArrowRight size={18} weight="bold" className="transition-transform group-hover:translate-x-1" />
            </a>
            <a
              href="#features"
              className="rounded-full border-2 border-[#141311] px-6 py-3 text-sm font-bold transition hover:bg-[#141311] hover:text-[#F6F5F3] active:scale-[0.98]"
            >
              See the features
            </a>
          </motion.div>
        </div>

        {/* Collage: three tilted overlapping photos */}
        <div className="relative h-[380px] md:col-span-5 md:h-[520px]">
          {[
            {
              seed: "sift-collage-sticky-note",
              alt: "A wall of sticky notes",
              cls: "right-0 top-0 w-[72%] -rotate-5",
              delay: 0.12,
            },
            {
              seed: "sift-collage-journal",
              alt: "An open journal on a couch",
              cls: "bottom-0 left-0 w-[64%] rotate-4",
              delay: 0.22,
            },
            {
              seed: "sift-collage-pocket-notes",
              alt: "Loose notes kept in a pocket",
              cls: "bottom-10 right-4 z-10 w-[44%] -rotate-2",
              delay: 0.32,
            },
          ].map((c) => (
            <motion.img
              key={c.seed}
              src={`https://picsum.photos/seed/${c.seed}/800/900`}
              alt={c.alt}
              width={800}
              height={900}
              initial={reduce ? false : { opacity: 0, y: 34, scale: 0.94 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              whileHover={reduce ? undefined : { scale: 1.04, zIndex: 20 }}
              transition={{ duration: 0.7, delay: c.delay, ease: EASE }}
              className={`absolute aspect-[4/5] rounded-3xl object-cover shadow-[0_24px_70px_-18px_rgb(20_19_17/0.4)] ring-1 ring-[#141311]/10 ${c.cls}`}
            />
          ))}
        </div>
      </section>

      {/* The page's one marquee */}
      <div className="marquee border-y-2 border-[#141311] bg-[#141311] py-4">
        <div className="marquee-track">
          {Array.from({ length: 8 }).map((_, i) => (
            <span key={i} className={`${DISPLAY} shrink-0 whitespace-nowrap pr-8 text-lg text-[#E2552C]`}>
              Capture → Sift → Keep → Recall →{" "}
            </span>
          ))}
        </div>
      </div>

      {/* Features: one horizontal snap rail, 5 items -> 5 cells */}
      <section id="features" className="scroll-mt-20 py-24 md:py-28">
        <div className="mx-auto max-w-7xl px-5 lg:px-8">
          <Reveal>
            <h2 className={`${DISPLAY} max-w-[14ch] text-5xl leading-[0.98] md:text-7xl`}>
              Everything in. Nothing lost.
            </h2>
          </Reveal>
        </div>
        <Reveal delay={0.1}>
          <div className="no-scrollbar mt-12 flex snap-x snap-mandatory gap-5 overflow-x-auto px-5 pb-2 lg:px-[max(1.25rem,calc((100vw-80rem)/2+1.25rem))]">
            {FEATURES.map((f) => (
              <article
                key={f.name}
                className="w-[78vw] shrink-0 snap-start overflow-hidden rounded-3xl bg-white ring-1 ring-[#E3E0DA] transition-transform hover:-translate-y-1.5 sm:w-[380px]"
              >
                <img
                  src={`https://picsum.photos/seed/${f.img}/760/480`}
                  alt=""
                  width={760}
                  height={480}
                  className="aspect-[19/12] w-full object-cover"
                />
                <div className="p-6">
                  <f.icon size={26} weight="bold" className="text-[#E2552C]" />
                  <h3 className={`${DISPLAY} mt-4 text-2xl`}>{f.name}</h3>
                  <p className="mt-2 font-sans text-[15px] leading-relaxed text-[#5A564E]">{f.line}</p>
                </div>
              </article>
            ))}
          </div>
        </Reveal>
      </section>

      {/* Statement */}
      <section className="border-t border-[#E3E0DA]">
        <div className="mx-auto max-w-7xl px-5 py-24 md:py-28 lg:px-8">
          <Reveal>
            <p className={`${DISPLAY} max-w-[17ch] text-5xl leading-[1.0] md:text-7xl`}>
              Notes should feel like a <span className="bg-[#E2552C] px-2 leading-[1.1]">pile</span>,
              not a spreadsheet.
            </p>
          </Reveal>
        </div>
      </section>

      {/* Voices: two quotes, hairline pairs */}
      <section id="voices" className="border-t border-[#E3E0DA]">
        <div className="mx-auto grid max-w-7xl gap-12 px-5 py-24 md:grid-cols-2 md:py-28 lg:px-8">
          {QUOTES.map((q, i) => (
            <Reveal key={q.name} delay={i * 0.08} className="border-t-4 border-[#E2552C] pt-6">
              <blockquote className="font-display text-2xl font-semibold leading-snug tracking-tight md:text-[28px]">
                &ldquo;{q.text}&rdquo;
              </blockquote>
              <p className="mt-5 font-sans text-sm font-medium text-[#5A564E]">
                {q.name} <span className="mx-2 text-[#C9C4BA]">/</span> {q.role}
              </p>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Big orange CTA block */}
      <section id="get" className="scroll-mt-20 bg-[#E2552C]">
        <div className="mx-auto max-w-7xl px-5 py-28 text-center md:py-36 lg:px-8">
          <Reveal>
            <h2 className={`${DISPLAY} mx-auto max-w-[10ch] text-6xl leading-[0.95] md:text-8xl`}>
              Get Sift
            </h2>
            <p className="mx-auto mt-6 max-w-[34ch] font-sans text-lg text-[#3B150A]">
              Free until your brain holds a thousand notes. Then five euros a month.
            </p>
            <a
              href="#"
              className="mt-9 inline-block rounded-full bg-[#141311] px-7 py-3.5 text-sm font-bold text-[#F6F5F3] transition hover:bg-[#2A2721] active:scale-[0.98]"
            >
              Get Sift
            </a>
          </Reveal>
        </div>
      </section>

      <footer className="bg-[#141311] text-[#B9B4AA]">
        <div className="mx-auto flex max-w-7xl flex-col justify-between gap-6 px-5 py-10 md:flex-row md:items-center lg:px-8">
          <p className={`${DISPLAY} text-xl text-[#F6F5F3]`}>
            Sift<span className="text-[#E2552C]">.</span>
          </p>
          <nav className="flex items-center gap-8 font-sans text-sm">
            <a href="#features" className="transition-colors hover:text-[#F6F5F3]">Features</a>
            <a href="#voices" className="transition-colors hover:text-[#F6F5F3]">Voices</a>
            <a href="#get" className="font-semibold text-[#E2552C]">Get Sift</a>
          </nav>
        </div>
      </footer>
    </div>
  );
});
