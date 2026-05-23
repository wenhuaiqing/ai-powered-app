// Lets any page open the orb with a pre-filled prompt or fire a specific
// agent directly. Mounted in App.jsx and consumed via useOrb() in module
// pages (the "Estimate value" / "Draft listing" / etc. buttons).

import { createContext, useCallback, useContext, useRef, useState } from "react";

const Ctx = createContext(null);

export function OrbProvider({ children }) {
  const [pending, setPending] = useState(null);
  // Pending is a one-shot signal the orb panel consumes when it mounts/opens.
  // Shape: { mode: "chat"|"run-agent", message?, agent?, inputs?, page_context? }
  const seq = useRef(0);

  const openWithPrompt = useCallback((message, page_context = {}) => {
    seq.current += 1;
    setPending({ id: seq.current, mode: "chat", message, page_context });
  }, []);

  const runAgent = useCallback((agent, inputs = {}, page_context = {}, message = "") => {
    seq.current += 1;
    setPending({ id: seq.current, mode: "run-agent", agent, inputs, message, page_context });
  }, []);

  // Just open the panel — no prompt submitted. Used by the "open Rai" hint
  // on the Dashboard so the user can type their own question.
  const openPanel = useCallback(() => {
    seq.current += 1;
    setPending({ id: seq.current, mode: "open" });
  }, []);

  const consume = useCallback(() => {
    setPending(null);
  }, []);

  return (
    <Ctx.Provider value={{ pending, openWithPrompt, runAgent, openPanel, consume }}>
      {children}
    </Ctx.Provider>
  );
}

export function useOrb() {
  return useContext(Ctx);
}
