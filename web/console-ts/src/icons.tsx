// Inline clinical icons (stroke style) — no icon-font dependency.
const I = (p: { d: string; fill?: boolean }) => (
  <svg viewBox="0 0 24 24" fill={p.fill ? "currentColor" : "none"} stroke="currentColor"
       strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d={p.d} />
  </svg>
);
export const IconShield = () => <I d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" />;
export const IconCheck = () => <I d="M20 6L9 17l-5-5" />;
export const IconAlert = () => <I d="M12 9v4m0 4h.01M10.3 3.9L1.8 18a2 2 0 001.7 3h17a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z" />;
export const IconHelp = () => <I d="M9.1 9a3 3 0 015.8 1c0 2-3 3-3 3m.1 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />;
export const IconDoc = () => <I d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm0 0v6h6" />;
export const IconBolt = () => <I d="M13 2L3 14h7l-1 8 10-12h-7l1-8z" />;
export const IconBuilding = () => <I d="M3 21h18M5 21V7l7-4 7 4v14M9 9h.01M9 13h.01M9 17h.01M15 9h.01M15 13h.01M15 17h.01" />;
export const IconCoin = () => <I d="M12 1v22M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />;
export const IconList = () => <I d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />;
export const IconClock = () => <I d="M12 7v5l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />;
