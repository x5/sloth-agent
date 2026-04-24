import { create } from "zustand";

export type AppStatus = "idle" | "working" | "error";

interface AppStatusState {
  status: AppStatus;
  setStatus: (status: AppStatus) => void;
}

export const useAppStatusStore = create<AppStatusState>((set) => ({
  status: "idle",
  setStatus: (status) => set({ status }),
}));
