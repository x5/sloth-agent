import { create } from "zustand";

export type Col4Content = "team" | "status" | null;
export type ActiveNav = "inspirations" | "agents" | "settings";
export type SettingsSubNav = "llm" | null;

interface UIState {
  col2Collapsed: boolean;
  col4Open: boolean;
  col4Content: Col4Content;
  activeNav: ActiveNav;
  settingsSubNav: SettingsSubNav;
  toggleCol2: () => void;
  openCol4: (content: Col4Content) => void;
  closeCol4: () => void;
  setActiveNav: (nav: ActiveNav) => void;
  setSettingsSubNav: (sub: SettingsSubNav) => void;
}

export const useUIStore = create<UIState>((set) => ({
  col2Collapsed: false,
  col4Open: false,
  col4Content: null,
  activeNav: "inspirations",
  settingsSubNav: null,

  toggleCol2: () => set((s) => ({ col2Collapsed: !s.col2Collapsed })),

  openCol4: (content) =>
    set((s) => {
      if (s.col4Open && s.col4Content === content) {
        return { col4Open: false, col4Content: null };
      }
      return { col4Open: true, col4Content: content };
    }),

  closeCol4: () => set({ col4Open: false, col4Content: null }),

  setActiveNav: (nav) => set({ activeNav: nav, col4Open: false, col4Content: null, settingsSubNav: nav === "settings" ? "llm" : null }),

  setSettingsSubNav: (sub) => set({ settingsSubNav: sub }),
}));
