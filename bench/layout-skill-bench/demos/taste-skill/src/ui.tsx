import { memo, type ReactNode } from "react";
import { motion, useReducedMotion } from "motion/react";

export const EASE = [0.16, 1, 0.3, 1] as const;

export const Reveal = memo(function Reveal({
  children,
  delay = 0,
  y = 24,
  className,
  once = true,
}: {
  children: ReactNode;
  delay?: number;
  y?: number;
  className?: string;
  once?: boolean;
}) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once, amount: 0.25 }}
      transition={{ duration: 0.6, delay, ease: EASE }}
    >
      {children}
    </motion.div>
  );
});

export const Marquee = memo(function Marquee({
  items,
  className,
  itemClassName,
}: {
  items: string[];
  className?: string;
  itemClassName?: string;
}) {
  const row = [...items, ...items];
  return (
    <div className={`marquee ${className ?? ""}`} aria-hidden="true">
      <div className="marquee-track">
        {row.map((item, i) => (
          <span key={i} className={`shrink-0 whitespace-nowrap ${itemClassName ?? ""}`}>
            {item}
          </span>
        ))}
      </div>
    </div>
  );
});

export const Monogram = memo(function Monogram({
  mark,
  className,
}: {
  mark: string;
  className?: string;
}) {
  return (
    <svg viewBox="0 0 40 40" role="img" aria-label={mark} className={className}>
      <circle cx="20" cy="20" r="19" fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.5" />
      <text
        x="20"
        y="25.5"
        textAnchor="middle"
        fontSize="15"
        fontWeight="600"
        letterSpacing="0.5"
        fill="currentColor"
        fontFamily="inherit"
      >
        {mark}
      </text>
    </svg>
  );
});
