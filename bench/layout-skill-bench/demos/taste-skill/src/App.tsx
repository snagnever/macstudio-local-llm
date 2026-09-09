import { useEffect, useState } from "react";
import Fathom from "./pages/1";
import Mnemo from "./pages/2";
import Marginalia from "./pages/3";
import Sift from "./pages/4";
import Attic from "./pages/5";

export const ITERATIONS = [
  { path: "/1", name: "Fathom", page: Fathom },
  { path: "/2", name: "mnemo", page: Mnemo },
  { path: "/3", name: "Marginalia", page: Marginalia },
  { path: "/4", name: "Sift", page: Sift },
  { path: "/5", name: "Attic", page: Attic },
] as const;

const PATHS: string[] = ITERATIONS.map((i) => i.path);

function normalize(pathname: string) {
  const clean = pathname.replace(/\/+$/, "");
  return PATHS.includes(clean) ? clean : "/1";
}

function navigate(path: string) {
  if (path === window.location.pathname) return;
  window.history.pushState({}, "", path);
  window.scrollTo({ top: 0, behavior: "instant" as ScrollBehavior });
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function usePath() {
  const [path, setPath] = useState(() => normalize(window.location.pathname));
  useEffect(() => {
    const sync = () => setPath(normalize(window.location.pathname));
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);
  return path;
}

function Switcher({ current }: { current: string }) {
  return (
    <nav
      aria-label="Switch design iteration"
      className="fixed bottom-5 left-1/2 z-[100] -translate-x-1/2 mix-blend-difference"
    >
      <div className="flex items-center gap-1 rounded-full border border-white/50 px-2 py-1.5">
        {ITERATIONS.map((it, i) => {
          const active = it.path === current;
          return (
            <button
              key={it.path}
              onClick={() => navigate(it.path)}
              title={`${it.path} ${it.name}`}
              aria-label={`Iteration ${i + 1}: ${it.name}`}
              aria-current={active ? "page" : undefined}
              className={`grid size-8 place-items-center rounded-full text-sm tabular-nums transition-transform hover:scale-110 active:scale-95 ${
                active ? "bg-white font-semibold text-black" : "text-white/90"
              }`}
            >
              {i + 1}
            </button>
          );
        })}
      </div>
    </nav>
  );
}

export default function App() {
  const path = usePath();
  const active = ITERATIONS.find((i) => i.path === path) ?? ITERATIONS[0];
  const Page = active.page;
  return (
    <>
      <Page />
      <Switcher current={active.path} />
    </>
  );
}
